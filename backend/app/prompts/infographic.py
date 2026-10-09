from app.schemas.output_schemas import InfographicOutput

SCHEMA = InfographicOutput.model_json_schema()

SYSTEM_TEMPLATE = """You are planning the content for an infographic based on the
source below. You are NOT generating an image — only the messaging and layout plan
a designer would use.

Tone: {tone}. Sentiment: {sentiment}. Audience: {audience}.
Language: {language}. Detail level: {detail_level}.

Requirements:
- key_messages: the 3-6 most important points, each short enough to fit on a visual
- sections: suggested section breakdown in reading order
- layout_recommendations: prose guidance on visual hierarchy, what should be
  emphasized largest/first, suggested icon or chart use per section

Respond only with JSON matching the required schema — no markdown, no preamble."""


def build_system_instruction(params: dict) -> str:
    return SYSTEM_TEMPLATE.format(**params)
