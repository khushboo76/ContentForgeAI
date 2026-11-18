"""
Official LinkedIn API integration:
- OAuth 2.0 Authorization Code flow with 'openid profile email w_member_social'
- Token exchange and Userinfo inspection
- Publishing text posts using LinkedIn Posts / UGC API
"""
import logging
from urllib.parse import urlencode

import httpx
from app.core import config

logger = logging.getLogger(__name__)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_REST_POSTS_URL = "https://api.linkedin.com/rest/posts"


def is_configured() -> bool:
    return bool(config.LINKEDIN_CLIENT_ID and config.LINKEDIN_CLIENT_SECRET)


def build_authorization_url(state: str) -> tuple[str, bool]:
    """
    Builds the 3-legged OAuth 2.0 authorization URL for LinkedIn.
    Returns (url, is_configured).
    """
    if not is_configured():
        return "", False

    params = {
        "response_type": "code",
        "client_id": config.LINKEDIN_CLIENT_ID,
        "redirect_uri": config.LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": "openid profile email w_member_social",
    }
    return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}", True


async def exchange_code_for_token(code: str) -> dict:
    """Exchanges authorization code for an access token."""
    if not is_configured():
        raise ValueError("LinkedIn OAuth is not configured")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.LINKEDIN_REDIRECT_URI,
        "client_id": config.LINKEDIN_CLIENT_ID,
        "client_secret": config.LINKEDIN_CLIENT_SECRET,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            LINKEDIN_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            logger.error("LinkedIn token exchange error: %s", response.text)
            raise ValueError(f"LinkedIn token exchange failed ({response.status_code}): {response.text[:200]}")
        return response.json()


async def fetch_user_profile(access_token: str) -> dict:
    """Retrieves authenticated member profile via LinkedIn OpenID userinfo."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(LINKEDIN_USERINFO_URL, headers=headers)
        if response.status_code >= 400:
            logger.error("LinkedIn userinfo error: %s", response.text)
            raise ValueError(f"Could not retrieve LinkedIn profile: {response.text[:200]}")
        return response.json()


async def publish_post(access_token: str, author_sub: str, text: str) -> dict:
    """
    Publishes a share post to the authenticated member's LinkedIn feed.
    Uses LinkedIn's current REST Posts API.
    """
    person_urn = author_sub if author_sub.startswith("urn:li:person:") else f"urn:li:person:{author_sub}"

    rest_payload = {
        "author": person_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": config.LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(LINKEDIN_REST_POSTS_URL, json=rest_payload, headers=headers)
        if response.status_code in (200, 201):
            post_urn = response.headers.get("x-restli-id") or response.headers.get("x-linkedin-id") or ""
            return {
                "id": post_urn or "published",
                "url": f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else "https://www.linkedin.com/feed/",
            }
        raise ValueError(
            f"LinkedIn post publication failed ({response.status_code}): {response.text[:300]}"
        )
