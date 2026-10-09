"""
Optional second-pass check: asks Gemini to score a generated output against
the requested tone/sentiment (1-5) and flags anything under threshold so the
caller can decide whether to regenerate.
"""
from app.core.gemini_client import generate

VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 1, "maximum": 5},
        "reasoning": {"type": "string"},
    },
    "required": ["score", "reasoning"],
}

VALIDATION_INSTRUCTION = """Rate, from 1 (poor match) to 5 (excellent match), how well
the following generated text matches the target tone "{tone}" and target sentiment
"{sentiment}". Give a one-sentence reason for your score.

Respond only with JSON matching the required schema."""


async def validate_tone(generated_text: str, tone: str, sentiment: str, threshold: int = 3) -> dict:
    result = await generate(
        system_instruction=VALIDATION_INSTRUCTION.format(tone=tone, sentiment=sentiment),
        source_content=generated_text,
        schema=VALIDATION_SCHEMA,
    )
    result["passed"] = result.get("score", 0) >= threshold
    return result
