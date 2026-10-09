from app.schemas.output_schemas import LinkedInPostOutput

SCHEMA = LinkedInPostOutput.model_json_schema()

SYSTEM_TEMPLATE = """You are a professional social media copywriter.
Generate a LinkedIn post based on the source content below.

Tone: {tone}. Sentiment: {sentiment}. Audience: {audience}.
Language: {language}. Detail level: {detail_level}.

Requirements:
- Hook in the first line that earns attention without clickbait
- Body should be scannable (short paragraphs), and factually grounded in the source
- 3-5 relevant hashtags
- Optional single call-to-action, only if it fits naturally

Respond only with JSON matching the required schema — no markdown, no preamble."""


def build_system_instruction(params: dict) -> str:
    return SYSTEM_TEMPLATE.format(**params)
