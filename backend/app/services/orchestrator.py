"""
Fans out one analyzed source to every selected output type. Calls are made
sequentially (not concurrently) on purpose — the free Gemini tier's RPM limit
means firing everything at once just trades one 429 storm for a slower,
back-off-heavy run. Sequential + backoff is simpler and demo-safe.

Extend to a bounded-concurrency queue (e.g. asyncio.Semaphore) once you have
a paid tier or need to shave latency for many simultaneous output types.
"""
import base64
from app.core.gemini_client import generate, generate_image
from app.prompts import get_template

DEFAULT_PARAMS = {
    "tone": "neutral-informative",
    "sentiment": "neutral",
    "audience": "general public",
    "language": "English",
    "detail_level": "standard",
}

# Output types that also get an actual rendered image generated (via Nano
# Banana) once their structured content comes back — not just layout text.
IMAGE_ENABLED_TYPES = {"infographic"}


async def _generate_infographic_image(data: dict) -> str | None:
    """
    Builds an image prompt from the already-generated infographic content and
    renders an actual visual. Returns a base64-encoded PNG string, or None if
    image generation fails (failure here should never break the text result).
    """
    key_messages = data.get("key_messages", [])
    layout = data.get("layout_recommendations", "")
    prompt = (
        "Create a clean, modern infographic image. "
        f"Key messages to visualize: {'; '.join(key_messages)}. "
        f"Layout guidance: {layout}"
    )
    try:
        image_bytes = await generate_image(prompt)
        return base64.b64encode(image_bytes).decode("utf-8")
    except Exception:
        return None


async def generate_all(
    source_content: str,
    output_types: list[str],
    params: dict | None = None,
    media_parts: list[tuple[bytes, str]] | None = None,
) -> dict:
    """
    source_content: normalized text from content_ingestion (may be empty
        string if the source is purely an image/video — see media_parts)
    output_types: list of keys matching app.prompts.REGISTRY (e.g. "linkedin_post")
    params: tone/sentiment/audience/language/detail_level overrides
    media_parts: optional list of (raw_bytes, mime_type) — an uploaded image
        or video passed as native multimodal input alongside/instead of text

    Returns: { output_type: { "status": "done"|"failed", "data": {...} | "error": str } }
    For "infographic", when successful, data also includes "image_base64"
    (a rendered visual) alongside the text content — image_base64 is None
    if image generation failed, without affecting the text result's status.
    """
    merged_params = {**DEFAULT_PARAMS, **(params or {})}
    results: dict = {}

    for output_type in output_types:
        try:
            template = get_template(output_type)
            system_instruction = template.build_system_instruction(merged_params)
            data = await generate(
                system_instruction=system_instruction,
                source_content=source_content,
                schema=template.SCHEMA,
                media_parts=media_parts,
            )

            if output_type in IMAGE_ENABLED_TYPES:
                data["image_base64"] = await _generate_infographic_image(data)

            results[output_type] = {"status": "done", "data": data}
        except Exception as exc:
            results[output_type] = {"status": "failed", "error": str(exc)}

    return results
