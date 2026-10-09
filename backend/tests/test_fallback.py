"""
Tests for the Gemini -> Mistral/Groq failover and local URL fallback.
No network or API keys needed: provider calls are monkeypatched.
"""
import asyncio

import pytest

from app.core import config, gemini_client, llm_fallback
from app.services import url_fetcher
from app.services.retry import RateLimitError


def run(coro):
    return asyncio.run(coro)


class FakeAPIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


# ---------- transient error classification ----------
def test_503_is_treated_as_transient():
    exc = FakeAPIError(503, "503 UNAVAILABLE. This model is currently experiencing high demand.")
    with pytest.raises(RateLimitError):
        gemini_client._raise_if_transient(exc)


def test_429_is_treated_as_transient():
    with pytest.raises(RateLimitError):
        gemini_client._raise_if_transient(FakeAPIError(429, "RESOURCE_EXHAUSTED"))


def test_400_is_not_treated_as_transient():
    with pytest.raises(FakeAPIError):
        gemini_client._raise_if_transient(FakeAPIError(400, "INVALID_ARGUMENT bad schema"))


# ---------- JSON extraction ----------
def test_extract_json_plain():
    assert llm_fallback._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_code_fence():
    assert llm_fallback._extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_preamble():
    assert llm_fallback._extract_json('Sure! Here you go: {"a": 1} Hope that helps') == {"a": 1}


def test_extract_json_rejects_non_object():
    with pytest.raises(ValueError):
        llm_fallback._extract_json("[1, 2, 3]")


# ---------- provider chain ----------
def _enable_both_providers(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "m-key")
    monkeypatch.setattr(config, "GROQ_API_KEY", "g-key")
    monkeypatch.setattr(config, "FALLBACK_ORDER", ["mistral", "groq"])


def test_provider_without_key_is_skipped(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "")
    monkeypatch.setattr(config, "GROQ_API_KEY", "g-key")
    monkeypatch.setattr(config, "FALLBACK_ORDER", ["mistral", "groq"])
    assert [p["name"] for p in llm_fallback._providers()] == ["groq"]


def test_next_provider_used_when_first_fails(monkeypatch):
    _enable_both_providers(monkeypatch)
    calls = []

    async def fake_call(provider, messages, use_json_mode=True):
        calls.append(provider["name"])
        if provider["name"] == "mistral":
            raise llm_fallback.FallbackError("mistral HTTP 503")
        return '{"hook": "hi"}'

    monkeypatch.setattr(llm_fallback, "_call_provider", fake_call)
    result = run(llm_fallback.generate_json("sys", "src", {"required": ["hook"]}))
    assert result == {"hook": "hi"}
    assert calls == ["mistral", "groq"]


def test_malformed_reply_is_retried_once_on_same_provider(monkeypatch):
    _enable_both_providers(monkeypatch)
    replies = iter(["not json at all", '{"hook": "ok"}'])
    calls = []

    async def fake_call(provider, messages, use_json_mode=True):
        calls.append(provider["name"])
        return next(replies)

    monkeypatch.setattr(llm_fallback, "_call_provider", fake_call)
    result = run(llm_fallback.generate_json("sys", "src", {"required": ["hook"]}))
    assert result == {"hook": "ok"}
    assert calls == ["mistral", "mistral"]


def test_missing_required_keys_rejected(monkeypatch):
    _enable_both_providers(monkeypatch)

    async def fake_call(provider, messages, use_json_mode=True):
        return '{"wrong": 1}'

    monkeypatch.setattr(llm_fallback, "_call_provider", fake_call)
    with pytest.raises(llm_fallback.FallbackError):
        run(llm_fallback.generate_json("sys", "src", {"required": ["hook"]}))


def test_no_provider_configured_raises(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "")
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    with pytest.raises(llm_fallback.FallbackError):
        run(llm_fallback.generate_json("sys", "src", {}))


# ---------- gemini_client.generate failover ----------
def test_generate_falls_back_when_gemini_overloaded(monkeypatch):
    async def gemini_down(*args, **kwargs):
        raise RateLimitError("503 UNAVAILABLE")

    async def fake_fallback(system_instruction, source_content, schema):
        return {"hook": "from fallback"}

    monkeypatch.setattr(gemini_client, "_gemini_generate", gemini_down)
    monkeypatch.setattr(llm_fallback, "is_configured", lambda: True)
    monkeypatch.setattr(llm_fallback, "generate_json", fake_fallback)

    result = run(gemini_client.generate("sys", "some text", {}))
    assert result == {"hook": "from fallback"}


def test_generate_does_not_fall_back_for_media(monkeypatch):
    async def gemini_down(*args, **kwargs):
        raise RateLimitError("503 UNAVAILABLE")

    monkeypatch.setattr(gemini_client, "_gemini_generate", gemini_down)
    monkeypatch.setattr(llm_fallback, "is_configured", lambda: True)

    with pytest.raises(RateLimitError):
        run(gemini_client.generate("sys", "", {}, media_parts=[(b"img", "image/png")]))


def test_generate_explains_missing_fallback_config(monkeypatch):
    async def gemini_down(*args, **kwargs):
        raise RateLimitError("503 UNAVAILABLE")

    monkeypatch.setattr(gemini_client, "_gemini_generate", gemini_down)
    monkeypatch.setattr(llm_fallback, "is_configured", lambda: False)

    with pytest.raises(RateLimitError, match="MISTRAL_API_KEY"):
        run(gemini_client.generate("sys", "some text", {}))


def test_non_transient_gemini_error_is_not_masked(monkeypatch):
    async def gemini_bad_request(*args, **kwargs):
        raise FakeAPIError(400, "INVALID_ARGUMENT")

    monkeypatch.setattr(gemini_client, "_gemini_generate", gemini_bad_request)
    monkeypatch.setattr(llm_fallback, "is_configured", lambda: True)

    with pytest.raises(FakeAPIError):
        run(gemini_client.generate("sys", "some text", {}))


# ---------- URL fallback ----------
def test_url_extraction_falls_back_to_local_fetch(monkeypatch):
    async def gemini_down(url):
        raise RateLimitError("503 UNAVAILABLE")

    async def fake_fetch(url):
        return "page text " * 50

    monkeypatch.setattr(gemini_client, "_gemini_extract_url_text", gemini_down)
    monkeypatch.setattr(gemini_client, "fetch_url_text", fake_fetch)
    assert run(gemini_client.extract_url_text("https://example.com")).startswith("page text")


def test_html_to_text_strips_scripts_and_styles():
    html = (
        "<html><head><title>t</title><style>.a{}</style></head><body>"
        "<script>alert(1)</script><h1>Headline</h1><p>First paragraph.</p>"
        "<nav>menu</nav><p>Second paragraph.</p></body></html>"
    )
    text = url_fetcher._html_to_text(html)
    assert "Headline" in text and "First paragraph." in text and "Second paragraph." in text
    assert "alert" not in text and "menu" not in text and ".a{}" not in text


def test_private_urls_are_blocked():
    with pytest.raises(ValueError):
        url_fetcher._assert_public_url("http://127.0.0.1:8000/admin")
    with pytest.raises(ValueError):
        url_fetcher._assert_public_url("ftp://example.com/file")
