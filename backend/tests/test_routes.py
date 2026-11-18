"""
Route and API tests using standard unittest and FastAPI TestClient.
"""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from app.core import security


class TestRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Trigger startup lifespan
        cls.client = TestClient(app)
        with TestClient(app) as _:
            pass

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_list_output_types(self):
        res = self.client.get("/api/output-types")
        self.assertEqual(res.status_code, 200)
        types = res.json()["output_types"]
        self.assertIn("linkedin_post", types)
        self.assertIn("advisory", types)
        self.assertIn("executive_summary", types)
        self.assertIn("presentation", types)
        self.assertIn("infographic", types)
        self.assertNotIn("video_package", types)
        self.assertEqual(len(types), 6)

    def test_generate_rejects_empty_output_types(self):
        res = self.client.post("/api/generate", json={"source_content": "hello", "output_types": []})
        self.assertEqual(res.status_code, 400)

    def test_generate_rejects_unknown_output_type(self):
        res = self.client.post("/api/generate", json={
            "source_content": "hello",
            "output_types": ["not_a_real_type"],
        })
        self.assertEqual(res.status_code, 400)

    def test_generate_rejects_empty_source(self):
        res = self.client.post("/api/generate", json={
            "source_content": "   ",
            "output_types": ["linkedin_post"],
        })
        self.assertEqual(res.status_code, 400)

    def test_ingest_url_rejects_invalid_url(self):
        res = self.client.post("/api/ingest-url", json={"url": "not-a-url"})
        self.assertEqual(res.status_code, 400)

    def test_oauth_authorize_url_generation(self):
        headers = {"X-User-Id": "test_operator_1"}
        # LinkedIn
        res_li = self.client.get("/api/auth/linkedin/authorize-url", headers=headers)
        self.assertEqual(res_li.status_code, 200)
        data_li = res_li.json()
        self.assertIn("authorization_url", data_li)
        self.assertIn("state", data_li)

        res_gmail = self.client.get("/api/auth/gmail/authorize-url", headers=headers)
        self.assertEqual(res_gmail.status_code, 200)
        self.assertEqual(res_gmail.json()["platform"], "gmail")

    def test_oauth_state_tampering_rejected(self):
        res = self.client.post(
            "/api/auth/linkedin/callback",
            json={"code": "sample_auth_code", "state": "tampered_or_invalid_state"},
        )
        self.assertEqual(res.status_code, 400)

    def test_account_connection_and_user_isolation(self):
        user_a = "user_alpha"
        user_b = "user_beta"

        # Generate state for user_a
        headers_a = {"X-User-Id": user_a}
        auth_res = self.client.get("/api/auth/linkedin/authorize-url", headers=headers_a)
        state_a = auth_res.json()["state"]

        # Callback for user_a
        with (
            patch("app.api.routes.linkedin.exchange_code_for_token", new=AsyncMock(return_value={"access_token": "test-token", "expires_in": 3600})),
            patch("app.api.routes.linkedin.fetch_user_profile", new=AsyncMock(return_value={"sub": "member-123", "name": "User Alpha", "email": "alpha@example.com"})),
        ):
            cb_res = self.client.post(
                "/api/auth/linkedin/callback",
                json={"code": "auth_code_alpha", "state": state_a},
            )
        self.assertEqual(cb_res.status_code, 200)
        account_id = cb_res.json()["account"]["id"]

        # user_a should see 1 account
        list_a = self.client.get("/api/accounts", headers=headers_a)
        self.assertEqual(list_a.status_code, 200)
        accounts_a = list_a.json()["accounts"]
        self.assertTrue(any(a["id"] == account_id for a in accounts_a))

        # user_b should NOT see user_a's account (User Isolation)
        headers_b = {"X-User-Id": user_b}
        list_b = self.client.get("/api/accounts", headers=headers_b)
        accounts_b = list_b.json()["accounts"]
        self.assertFalse(any(a["id"] == account_id for a in accounts_b))

        # user_b cannot publish through user_a's account
        pub_b = self.client.post(
            "/api/publish/linkedin",
            headers=headers_b,
            json={"account_id": account_id, "text": "Unauthorized post"},
        )
        self.assertEqual(pub_b.status_code, 404)

        # user_a CAN publish through their own account
        with patch("app.api.routes.linkedin.publish_post", new=AsyncMock(return_value={"id": "urn:li:share:123", "url": "https://www.linkedin.com/feed/update/urn:li:share:123/"})):
            pub_a = self.client.post(
                "/api/publish/linkedin",
                headers=headers_a,
                json={"account_id": account_id, "text": "Authorized post from User Alpha"},
            )
        self.assertEqual(pub_a.status_code, 200)
        self.assertEqual(pub_a.json()["status"], "published")

        # user_a publication history should reflect the publish
        hist = self.client.get("/api/publish/history", headers=headers_a)
        self.assertEqual(hist.status_code, 200)
        self.assertTrue(len(hist.json()["publications"]) >= 1)

    def test_send_email_requires_a_connected_gmail_account(self):
        headers = {"X-User-Id": "email_tester"}
        res = self.client.post(
            "/api/publish/email",
            headers=headers,
            json={
                "recipients": ["team@example.com"],
                "subject": "Executive Briefing",
                "body_text": "Key findings from quarterly assessment.",
                "output_type": "executive_summary",
            },
        )
        self.assertEqual(res.status_code, 422)

    def test_gmail_send_uses_connected_account(self):
        headers = {"X-User-Id": "gmail_tester"}
        authorize = self.client.get("/api/auth/gmail/authorize-url", headers=headers).json()
        self.assertIn("state", authorize)
        state = authorize["state"]
        with (
            patch("app.api.routes.gmail.exchange_code_for_token", new=AsyncMock(return_value={"access_token": "gmail-token", "refresh_token": "gmail-refresh", "expires_in": 3600})),
            patch("app.api.routes.gmail.fetch_user_profile", new=AsyncMock(return_value={"sub": "google-123", "name": "Gmail Tester", "email": "tester@example.com"})),
        ):
            callback = self.client.post("/api/auth/gmail/callback", json={"code": "google-code", "state": state})
        account_id = callback.json()["account"]["id"]

        with patch(
            "app.api.routes.gmail.send_gmail_message",
            new=AsyncMock(return_value=({"id": "gmail-message-123", "threadId": "thread-123"}, None)),
        ):
            res = self.client.post(
                "/api/publish/email",
                headers=headers,
                json={
                    "account_id": account_id,
                    "recipients": ["client@example.com"],
                    "subject": "Gmail API Test",
                    "body_text": "Sent via Gmail API.",
                },
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["channel"], "gmail")



if __name__ == "__main__":
    unittest.main()
