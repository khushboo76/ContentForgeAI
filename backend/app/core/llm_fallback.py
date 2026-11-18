"""
Fallback text generation through OpenAI-compatible chat APIs (Mistral, Groq).

Used by gemini_client.generate() when Gemini is overloaded or rate limited
(HTTP 429/503/etc.) and still failing after its own retries. Providers are
tried in config.FALLBACK_ORDER; a provider with no API key is skipped.

Fallback models are text-only and do not enforce a response schema the way
Gemini does, so the schema is added to the prompt, the reply is parsed
defensively, and required top-level keys are checked before returning.
"""
import json
import logging
import re

import httpx

from app.core import config

logger = logging.getLogger(__name__)

# A malformed reply (not JSON / missing keys) is retried once on the same
# provider before moving on. HTTP errors move on immediately.
MAX_FORMAT_ATTEMPTS = 2


class FallbackError(RuntimeError):
    """Raised when a fallback provider call fails or returns unusable output."""


def _providers(provider_names: list[str] | None = None) -> list[dict]:
    registry = {
        "mistral": {
            "name": "mistral",
            "base_url": config.MISTRAL_BASE_URL,
            "api_key": config.MISTRAL_API_KEY,
            "model": config.MISTRAL_MODEL,
        },
        "groq": {
            "name": "groq",
            "base_url": config.GROQ_BASE_URL,
            "api_key": config.GROQ_API_KEY,
            "model": config.GROQ_MODEL,
        },
    }
    names = provider_names if provider_names is not None else config.FALLBACK_ORDER
    return [
        registry[name]
        for name in names
        if name in registry and registry[name]["api_key"]
    ]


def is_configured() -> bool:
    return bool(_providers())


def _build_messages(system_instruction: str, source_content: str, schema: dict) -> list[dict]:
    system = (
        f"{system_instruction}\n\n"
        "Return ONLY one valid JSON object — no markdown fences, no commentary — "
        "that matches this JSON Schema exactly:\n"
        f"{json.dumps(schema)}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": source_content},
    ]


def _extract_json(text: str) -> dict:
    """Parses a model reply into a dict, tolerating code fences and preamble."""
    cleaned = (text or "").strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        data = json.loads(cleaned[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Model reply was JSON but not an object")
    return data


def _missing_required(data: dict, schema: dict) -> list[str]:
    return [key for key in schema.get("required", []) if key not in data]


async def _call_provider(provider: dict, messages: list[dict], use_json_mode: bool = True) -> str:
    """One chat-completions request. Returns the assistant message text."""
    payload: dict = {
        "model": provider["model"],
        "messages": messages,
        "temperature": 0.4,
    }
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        async with httpx.AsyncClient(timeout=config.FALLBACK_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{provider['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {provider['api_key']}"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise FallbackError(f"{provider['name']} request failed: {exc!r}") from exc

    # Some models reject json mode; retry once without it.
    if response.status_code == 400 and use_json_mode:
        return await _call_provider(provider, messages, use_json_mode=False)

    if response.status_code >= 400:
        raise FallbackError(
            f"{provider['name']} HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise FallbackError(f"{provider['name']} returned an unexpected response shape") from exc


async def generate_json(
    system_instruction: str,
    source_content: str,
    schema: dict,
    provider_names: list[str] | None = None,
) -> dict:
    """
    Generates structured output via the first working fallback provider.
    Raises FallbackError if none are configured or all of them fail.
    """
    providers = _providers(provider_names)
    if not providers:
        raise FallbackError(
            "No fallback provider configured — set MISTRAL_API_KEY or GROQ_API_KEY in backend/.env"
        )

    messages = _build_messages(system_instruction, source_content, schema)
    failures: list[str] = []

    for provider in providers:
        for attempt in range(1, MAX_FORMAT_ATTEMPTS + 1):
            try:
                text = await _call_provider(provider, messages)
            except FallbackError as exc:
                failures.append(str(exc))
                break  # HTTP-level failure: go straight to the next provider

            try:
                data = _extract_json(text)
            except (json.JSONDecodeError, ValueError) as exc:
                failures.append(f"{provider['name']} attempt {attempt}: invalid JSON ({exc})")
                continue

            missing = _missing_required(data, schema)
            if missing:
                failures.append(f"{provider['name']} attempt {attempt}: missing keys {missing}")
                continue

            logger.info("Generated via fallback provider: %s", provider["name"])
            return data

    raise FallbackError("All fallback providers failed: " + " | ".join(failures))
