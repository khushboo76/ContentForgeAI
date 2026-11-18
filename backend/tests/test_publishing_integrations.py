"""Network-isolated contract tests for the live Gmail and LinkedIn integrations."""
import base64
import json
import unittest
from email import message_from_bytes
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx

from app.services.publishing import gmail, linkedin
from app.api import routes
from app.core import security
from app.core.database import SessionLocal, init_db
from app.models.db_models import ConnectedAccount, PublicationRecord
from app.services import account_service

REAL_ASYNC_CLIENT = httpx.AsyncClient


class MockAsyncClient:
    """Small AsyncClient replacement backed by an in-process HTTPX transport."""

    def __init__(self, *args, **kwargs):
        self.client = REAL_ASYNC_CLIENT(transport=kwargs.pop("transport"), *args, **kwargs)

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, *args):
        await self.client.aclose()


class TestPublishingIntegrations(unittest.IsolatedAsyncioTestCase):
    async def test_gmail_callback_stores_encrypted_account_then_sends_with_it(self):
        init_db()
        db = SessionLocal()
        user_id = "gmail-integration-test-user"
        state = security.create_oauth_state(user_id=user_id, platform="gmail")
        try:
            with (
                patch("app.api.routes.gmail.exchange_code_for_token", return_value={"access_token": "google-access", "refresh_token": "google-refresh", "expires_in": 3600}),
                patch("app.api.routes.gmail.fetch_user_profile", return_value={"sub": "google-user-1", "name": "Google User", "email": "user@example.com"}),
            ):
                callback = await routes.oauth_callback(
                    "gmail",
                    routes.OAuthCallbackRequest(code="authorization-code", state=state),
                    db,
                )

            account_id = callback["account"]["id"]
            account = account_service.get_account_for_user(db, user_id, account_id)
            self.assertIsNotNone(account)
            self.assertNotEqual(account.encrypted_access_token, "google-access")
            self.assertEqual(account_service.get_decrypted_tokens(account), ("google-access", "google-refresh"))

            with patch(
                "app.api.routes.gmail.send_gmail_message",
                return_value=({"id": "message-1", "threadId": "thread-1", "mode": "live"}, None),
            ) as send:
                response = await routes.send_deliverable_email(
                    routes.SendEmailRequest(
                        account_id=account_id,
                        recipients=["recipient@example.com"],
                        subject="Integration test",
                        body_text="Plain body",
                    ),
                    user_id,
                    db,
                )

            self.assertEqual(response["channel"], "gmail")
            self.assertEqual(response["sender"], "user@example.com")
            self.assertEqual(send.await_args.kwargs["access_token"], "google-access")
            self.assertEqual(send.await_args.kwargs["refresh_token"], "google-refresh")
        finally:
            db.query(PublicationRecord).filter(PublicationRecord.user_id == user_id).delete()
            db.query(ConnectedAccount).filter(ConnectedAccount.user_id == user_id).delete()
            db.commit()
            db.close()

    def test_gmail_authorization_url_requests_offline_send_permission(self):
        with (
            patch.object(gmail.config, "GOOGLE_CLIENT_ID", "google-client-id"),
            patch.object(gmail.config, "GOOGLE_CLIENT_SECRET", "google-client-secret"),
            patch.object(gmail.config, "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/gmail/callback"),
        ):
            url, configured = gmail.build_authorization_url("verified-state")

        query = parse_qs(urlparse(url).query)
        self.assertTrue(configured)
        self.assertEqual(query["state"], ["verified-state"])
        self.assertEqual(query["access_type"], ["offline"])
        self.assertEqual(query["prompt"], ["consent"])
        self.assertIn("https://www.googleapis.com/auth/gmail.send", query["scope"][0])

    def test_linkedin_authorization_url_includes_required_oauth_parameters(self):
        with (
            patch.object(linkedin.config, "LINKEDIN_CLIENT_ID", "linkedin-client-id"),
            patch.object(linkedin.config, "LINKEDIN_CLIENT_SECRET", "linkedin-client-secret"),
            patch.object(linkedin.config, "LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/auth/linkedin/callback"),
        ):
            url, configured = linkedin.build_authorization_url("verified-state")

        query = parse_qs(urlparse(url).query)
        self.assertTrue(configured)
        self.assertEqual(query["client_id"], ["linkedin-client-id"])
        self.assertEqual(query["state"], ["verified-state"])
        self.assertEqual(query["redirect_uri"], ["http://localhost:8000/api/auth/linkedin/callback"])
        self.assertIn("w_member_social", query["scope"][0])

    async def test_gmail_token_profile_and_send_flow_uses_google_endpoints(self):
        requests = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url == httpx.URL(gmail.GOOGLE_TOKEN_URL):
                self.assertEqual(request.method, "POST")
                self.assertIn(b"grant_type=authorization_code", request.content)
                return httpx.Response(200, json={"access_token": "google-access", "refresh_token": "google-refresh", "expires_in": 3600})
            if request.url == httpx.URL(gmail.GOOGLE_USERINFO_URL):
                self.assertEqual(request.headers["authorization"], "Bearer google-access")
                return httpx.Response(200, json={"sub": "google-user-1", "name": "Google User", "email": "user@example.com"})
            if request.url == httpx.URL(gmail.GMAIL_SEND_URL):
                self.assertEqual(request.headers["authorization"], "Bearer google-access")
                return httpx.Response(200, json={"id": "message-1", "threadId": "thread-1"})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        with (
            patch.object(gmail.config, "GOOGLE_CLIENT_ID", "google-client-id"),
            patch.object(gmail.config, "GOOGLE_CLIENT_SECRET", "google-client-secret"),
            patch.object(gmail.config, "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/gmail/callback"),
            patch("app.services.publishing.gmail.httpx.AsyncClient", lambda *args, **kwargs: MockAsyncClient(*args, transport=transport, **kwargs)),
        ):
            tokens = await gmail.exchange_code_for_token("authorization-code")
            profile = await gmail.fetch_user_profile(tokens["access_token"])
            result, refreshed = await gmail.send_gmail_message(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                sender_email=profile["email"],
                recipients=["recipient@example.com"],
                subject="Integration test",
                body_text="Plain body",
                body_html="<p>HTML body</p>",
            )

        self.assertEqual(profile["email"], "user@example.com")
        self.assertEqual(result["id"], "message-1")
        self.assertIsNone(refreshed)
        self.assertEqual(len(requests), 3)

    async def test_gmail_sends_rfc2822_message_to_live_api_endpoint(self):
        captured = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["request"] = request
            return httpx.Response(200, json={"id": "message-1", "threadId": "thread-1"})

        transport = httpx.MockTransport(handler)
        with patch("app.services.publishing.gmail.httpx.AsyncClient", lambda *args, **kwargs: MockAsyncClient(*args, transport=transport, **kwargs)):
            result, refreshed = await gmail.send_gmail_message(
                access_token="live-access-token",
                refresh_token=None,
                sender_email="sender@example.com",
                recipients=["recipient@example.com"],
                subject="Integration test",
                body_text="Plain body",
                body_html="<p>HTML body</p>",
            )

        self.assertIsNone(refreshed)
        self.assertEqual(result["id"], "message-1")
        self.assertEqual(captured["request"].url, httpx.URL(gmail.GMAIL_SEND_URL))
        self.assertEqual(captured["request"].headers["authorization"], "Bearer live-access-token")
        raw = json.loads(captured["request"].content)["raw"]
        decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        message = message_from_bytes(decoded)
        self.assertEqual(message["To"], "recipient@example.com")
        self.assertEqual(message.get_payload(0).get_payload(decode=True).decode(), "Plain body")

    async def test_linkedin_posts_to_rest_api_with_required_headers(self):
        captured = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["request"] = request
            return httpx.Response(201, headers={"x-restli-id": "urn:li:share:456"})

        transport = httpx.MockTransport(handler)
        with patch("app.services.publishing.linkedin.httpx.AsyncClient", lambda *args, **kwargs: MockAsyncClient(*args, transport=transport, **kwargs)):
            result = await linkedin.publish_post("live-access-token", "member-123", "A live post")

        self.assertEqual(result["id"], "urn:li:share:456")
        self.assertEqual(captured["request"].url, httpx.URL(linkedin.LINKEDIN_REST_POSTS_URL))
        self.assertEqual(captured["request"].headers["authorization"], "Bearer live-access-token")
        self.assertEqual(captured["request"].headers["linkedin-version"], linkedin.config.LINKEDIN_API_VERSION)
        payload = json.loads(captured["request"].content)
        self.assertEqual(payload["author"], "urn:li:person:member-123")
        self.assertEqual(payload["commentary"], "A live post")
