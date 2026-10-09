"""
Local URL fetching + HTML-to-text, used only as a fallback when Gemini's
url_context tool is unavailable (overloaded / rate limited).

Because this runs on the server, it refuses to fetch private, loopback, or
link-local addresses (SSRF protection) and re-checks every redirect hop.
"""
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

MAX_CHARS = 30_000
MIN_CHARS = 200
MAX_REDIRECTS = 5

_SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "nav", "footer", "form", "iframe"}
_BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "tr", "section", "article",
               "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self._parts.append(data.strip() + " ")

    def text(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


def _assert_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Please provide a full URL starting with http:// or https://")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host '{parsed.hostname}'") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("That URL points to a private or internal address and was blocked.")


async def fetch_url_text(url: str) -> str:
    """Fetches a page directly and returns its readable text."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentTransformBot/1.0)"}
    current = url
    async with httpx.AsyncClient(timeout=20, follow_redirects=False, headers=headers) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _assert_public_url(current)
            response = await client.get(current)
            if response.is_redirect and response.headers.get("location"):
                current = urljoin(current, response.headers["location"])
                continue
            response.raise_for_status()
            break
        else:
            raise ValueError("Too many redirects")

    content_type = response.headers.get("content-type", "").lower()
    if "html" in content_type:
        text = _html_to_text(response.text)
    elif content_type.startswith("text/"):
        text = response.text.strip()
    else:
        raise ValueError(f"Cannot read '{content_type or 'unknown'}' content without Gemini.")

    text = text[:MAX_CHARS]
    if len(text) < MIN_CHARS:
        raise ValueError("The page had too little readable text (it may need JavaScript to load).")
    return text
