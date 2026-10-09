"""
Wraps calls to the Gemini API: sends a system instruction + source content,
requests structured JSON output matching a given schema.

Resilience:
- Transient failures (429 rate limit, 500/502/503/504 overload, timeouts) are
  retried with exponential backoff (see services/retry.py).
- If Gemini is still failing, `generate()` switches to a fallback provider
  (Mistral/Groq, see llm_fallback.py) for text-only requests, and
  `extract_url_text()` fetches the page locally (see url_fetcher.py).

Also provides:
- extract_url_text: uses Gemini's url_context tool to fetch and read a URL.
- generate_image: Gemini's native image model ("Nano Banana"), used for the
  Infographic output type. Gemini-only — there is no fallback for images.
- Multimodal source support in `generate()`: pass `media_parts` to include
  image/video bytes as native input. Media requests are Gemini-only because
  fallback providers are text-only.
"""
import json
import logging

import httpx
from google import genai
from google.genai import types

from app.core import llm_fallback
from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_IMAGE_MODEL,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
)
from app.services.retry import RateLimitError, with_backoff
from app.services.url_fetcher import fetch_url_text

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
TRANSIENT_MARKERS = (
    "resource_exhausted",
    "unavailable",
    "deadline_exceeded",
    "high demand",
    "overloaded",
)


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set — copy .env.example to .env and add your key.")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _raise_if_transient(exc: Exception) -> None:
    """
    Re-raises `exc` as RateLimitError when it looks transient (rate limit,
    overload, timeout) so @with_backoff retries it and generate() can fail
    over to a fallback. Any other error (bad request, auth) is re-raised
    unchanged — retrying or falling back would only hide a real bug.
    """
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    text = str(exc)
    if (
        status in TRANSIENT_STATUS_CODES
        or isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))
        or any(marker in text.lower() for marker in TRANSIENT_MARKERS)
    ):
        raise RateLimitError(text) from exc
    raise exc


# ----------------------------------------------------------------------------
# Structured text generation
# ----------------------------------------------------------------------------
@with_backoff(max_retries=GEMINI_MAX_RETRIES, base_delay=1.0, max_delay=16.0)
async def _gemini_generate(
    system_instruction: str,
    source_content: str,
    schema: dict,
    media_parts: list[tuple[bytes, str]] | None,
) -> dict:
    client = _get_client()

    contents: list = [source_content] if source_content else []
    for data, mime_type in media_parts or []:
        contents.append(types.Part.from_bytes(data=data, mime_type=mime_type))

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
    except Exception as exc:
        _raise_if_transient(exc)

    return json.loads(response.text)


async def generate(
    system_instruction: str,
    source_content: str,
    schema: dict,
    media_parts: list[tuple[bytes, str]] | None = None,
) -> dict:
    """
    Generates structured output conforming to `schema`. Returns the parsed dict.

    Tries Gemini first (with retries). If Gemini is still unavailable and the
    request is text-only, falls back to Mistral/Groq. media_parts, when given,
    are passed to Gemini as native multimodal input (Gemini-only).
    """
    try:
        return await _gemini_generate(system_instruction, source_content, schema, media_parts)
    except RateLimitError as gemini_exc:
        if media_parts or not source_content:
            raise  # fallback providers can't read images/video

        if not llm_fallback.is_configured():
            raise RateLimitError(
                f"{gemini_exc}\n\nNo fallback provider is configured — set MISTRAL_API_KEY "
                "or GROQ_API_KEY in backend/.env to survive Gemini outages."
            ) from gemini_exc

        logger.warning("Gemini unavailable (%s); switching to fallback provider", gemini_exc)
        try:
            return await llm_fallback.generate_json(system_instruction, source_content, schema)
        except llm_fallback.FallbackError as fallback_exc:
            raise RuntimeError(
                f"Gemini unavailable: {gemini_exc}\nFallback failed: {fallback_exc}"
            ) from fallback_exc


# ----------------------------------------------------------------------------
# URL extraction
# ----------------------------------------------------------------------------
@with_backoff(max_retries=GEMINI_MAX_RETRIES, base_delay=1.0, max_delay=16.0)
async def _gemini_extract_url_text(url: str) -> str:
    client = _get_client()
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"Extract the full readable text content from this page: {url}",
            config=types.GenerateContentConfig(tools=[{"url_context": {}}]),
        )
    except Exception as exc:
        _raise_if_transient(exc)

    text = (response.text or "").strip()
    if not text:
        raise ValueError(f"Could not extract any readable content from {url}")
    return text


async def extract_url_text(url: str) -> str:
    """
    Reads a URL via Gemini's url_context tool. If Gemini is unavailable, fetches
    the page directly and strips the HTML instead (works for normal article
    pages, not JavaScript-only sites).
    """
    try:
        return await _gemini_extract_url_text(url)
    except RateLimitError as gemini_exc:
        logger.warning("Gemini unavailable (%s); fetching URL locally", gemini_exc)
        try:
            return await fetch_url_text(url)
        except (ValueError, httpx.HTTPError) as local_exc:
            raise RuntimeError(
                f"Gemini unavailable: {gemini_exc}\nLocal fetch failed: {local_exc}"
            ) from local_exc


# ----------------------------------------------------------------------------
# Image generation (Gemini-only)
# ----------------------------------------------------------------------------
@with_backoff(max_retries=GEMINI_MAX_RETRIES, base_delay=1.0, max_delay=16.0)
async def generate_image(prompt: str) -> bytes:
    """
    Calls Gemini's native image-generation model ("Nano Banana") and returns
    the raw image bytes. Used for the Infographic output type.
    """
    client = _get_client()
    try:
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=prompt,
        )
    except Exception as exc:
        _raise_if_transient(exc)

    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            if part.inline_data is not None:
                return part.inline_data.data

    raise ValueError("Gemini did not return an image for this prompt.")
