from app.schemas.output_schemas import PresentationOutput

SCHEMA = PresentationOutput.model_json_schema()

SYSTEM_TEMPLATE = """You are creating presentation slide content from the source below.

Tone: {tone}. Sentiment: {sentiment}. Audience: {audience}.
Language: {language}. Detail level: {detail_level}.

Requirements:
- Produce a reasonable number of slides for the content's depth (typically 4-10)
- Each slide: a short title, 2-4 bullets (not full sentences), and speaker_notes
  that expand on the bullets in prose for whoever presents it
- Keep bullets scannable — no bullet should be a paragraph

Respond only with JSON matching the required schema — no markdown, no preamble."""


def build_system_instruction(params: dict) -> str:
    return SYSTEM_TEMPLATE.format(**params)
