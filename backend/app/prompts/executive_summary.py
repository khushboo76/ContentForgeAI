from app.schemas.output_schemas import ExecutiveSummaryOutput

SCHEMA = ExecutiveSummaryOutput.model_json_schema()

SYSTEM_TEMPLATE = """You are preparing an executive briefing for leadership who have
limited time and need the essence of the source content, not the full detail.

Tone: {tone}. Sentiment: {sentiment}. Audience: {audience}.
Language: {language}. Detail level: {detail_level}.

Requirements:
- summary: 3-5 sentences capturing the core of the source content
- key_findings: bullet-worthy, most important facts only
- recommendations: only if the source supports them — do not invent recommendations

Respond only with JSON matching the required schema — no markdown, no preamble."""


def build_system_instruction(params: dict) -> str:
    return SYSTEM_TEMPLATE.format(**params)
