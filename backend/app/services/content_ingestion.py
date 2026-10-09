"""
Extracts and normalizes source content submitted on the dashboard.
Text/pasted content passes straight through. Documents are extracted to
text. URLs are read via Gemini's url_context tool. Images/video are read
as raw bytes and passed through as native multimodal input — NOT extracted
to text — since Gemini accepts them directly (see gemini_client.generate's
media_parts param).
"""
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from app.core.gemini_client import extract_url_text

SUPPORTED_DOCUMENT_TYPES = {".txt", ".md", ".pdf", ".docx"}

SUPPORTED_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}


def ingest_text(raw_text: str) -> str:
    """Normalizes pasted/typed source content."""
    text = raw_text.strip()
    if not text:
        raise ValueError("source_content is empty after normalization")
    return text


def ingest_file(file_path: str) -> str:
    """Extracts plain text from an uploaded document."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_DOCUMENT_TYPES:
        raise NotImplementedError(
            f"No text-extraction handler for '{suffix}' files. "
            f"Supported documents: {', '.join(sorted(SUPPORTED_DOCUMENT_TYPES))}. "
            f"Image/video files should go through ingest_media_file instead — "
            f"they're passed to Gemini as native multimodal input, not extracted to text."
        )

    if suffix in {".txt", ".md"}:
        return ingest_text(path.read_text(encoding="utf-8"))

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return ingest_text("\n\n".join(pages))

    if suffix == ".docx":
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return ingest_text("\n\n".join(paragraphs))

    raise AssertionError("unreachable — suffix checked above")


async def ingest_url(url: str) -> str:
    """
    Fetches and extracts readable text from a URL using Gemini's url_context
    tool. Returns plain text, so it slots into the existing text pipeline
    (orchestrator, prompt templates) with no other changes needed.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("Please provide a full URL starting with http:// or https://")
    return await extract_url_text(url)


def ingest_media_file(file_path: str) -> tuple[bytes, str]:
    """
    Reads an uploaded image or video as raw bytes + mime type, for use as
    native multimodal input (see gemini_client.generate's media_parts param).
    Deliberately does NOT try to extract text — Gemini understands the
    image/video directly.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_MEDIA_TYPES:
        raise NotImplementedError(
            f"No handler for '{suffix}' media files. "
            f"Supported: {', '.join(sorted(SUPPORTED_MEDIA_TYPES))}."
        )

    mime_type = SUPPORTED_MEDIA_TYPES[suffix]
    return path.read_bytes(), mime_type
