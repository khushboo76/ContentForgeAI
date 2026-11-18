"""
Official Google Gmail API v1 integration:
- OAuth 2.0 Authorization Code flow with offline access & refresh tokens
- Scopes: 'openid email profile https://www.googleapis.com/auth/gmail.send'
- Direct RFC 2822 base64url email transmission via POST /gmail/v1/users/me/messages/send
- Automatic refresh token rotation when access token expires
"""
import base64
import logging
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from urllib.parse import urlencode

import httpx
from app.core import config

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
]


def is_configured() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET)


def build_authorization_url(state: str) -> tuple[str, bool]:
    """Builds the Google OAuth 2.0 authorization URL requesting gmail.send scope."""
    if not is_configured():
        return "", False

    params = {
        "response_type": "code",
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": config.GOOGLE_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",   # guarantees refresh_token
        "prompt": "consent",        # ensures refresh_token on re-authorization
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}", True


async def exchange_code_for_token(code: str) -> dict:
    """Exchanges Google authorization code for access & refresh tokens."""
    if not is_configured():
        raise ValueError("Google OAuth is not configured")

    data = {
        "code": code,
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "redirect_uri": config.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        if response.status_code >= 400:
            logger.error("Google token exchange error: %s", response.text)
            raise ValueError(f"Google token exchange failed ({response.status_code}): {response.text[:200]}")
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Refreshes an expired Google access token using the stored refresh token."""
    data = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        if response.status_code >= 400:
            logger.error("Google token refresh error: %s", response.text)
            raise ValueError(f"Failed to refresh Google token: {response.text[:200]}")
        return response.json()


async def fetch_user_profile(access_token: str) -> dict:
    """Retrieves authenticated user profile (email and display name)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        if response.status_code >= 400:
            logger.error("Google userinfo error: %s", response.text)
            raise ValueError(f"Could not retrieve Google profile: {response.text[:200]}")
        return response.json()


def create_rfc2822_raw(
    sender_email: str,
    recipients: list[str],
    subject: str,
    body_text: str,
    body_html: str,
) -> str:
    """Creates a MIME multipart email and encodes it as base64url for Gmail API."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr(("ContentForge AI", sender_email))
    msg["To"] = ", ".join(recipients)
    msg["Date"] = formatdate(localtime=True)

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # Gmail API requires standard RFC 4648 base64url encoding without padding
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii").rstrip("=")


async def send_gmail_message(
    access_token: str,
    refresh_token: str | None,
    sender_email: str,
    recipients: list[str],
    subject: str,
    body_text: str,
    body_html: str,
) -> tuple[dict, str | None]:
    """
    Sends an email using the official Gmail API v1 messages.send endpoint.
    Automatically refreshes token if expired.
    Returns (result_dict, new_access_token_if_refreshed).
    """
    if not recipients:
        raise ValueError("At least one recipient is required")

    raw_message = create_rfc2822_raw(sender_email, recipients, subject, body_text, body_html)
    payload = {"raw": raw_message}

    new_access_token = None
    token_to_use = access_token

    async with httpx.AsyncClient(timeout=30.0) as client:
        # First attempt
        headers = {
            "Authorization": f"Bearer {token_to_use}",
            "Content-Type": "application/json",
        }
        response = await client.post(GMAIL_SEND_URL, json=payload, headers=headers)

        # If expired and we have a refresh_token, refresh and retry once
        if response.status_code == 401 and refresh_token:
            logger.info("Gmail access token expired, refreshing...")
            token_data = await refresh_access_token(refresh_token)
            token_to_use = token_data["access_token"]
            new_access_token = token_to_use
            headers["Authorization"] = f"Bearer {token_to_use}"
            response = await client.post(GMAIL_SEND_URL, json=payload, headers=headers)

        if response.status_code not in (200, 201):
            logger.error("Gmail API send error (%s): %s", response.status_code, response.text)
            raise ValueError(f"Gmail send failed ({response.status_code}): {response.text[:250]}")

        data = response.json()
        return {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "recipients": recipients,
            "subject": subject,
            "sender": sender_email,
            "mode": "live",
        }, new_access_token
