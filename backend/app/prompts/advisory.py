from app.schemas.output_schemas import AdvisoryOutput

SCHEMA = AdvisoryOutput.model_json_schema()

SYSTEM_TEMPLATE = """You are drafting a formal advisory document for operational use.
Base every statement strictly on the source content — do not speculate or add
unverified claims, especially regarding severity or recommended actions.

Tone: {tone}. Sentiment: {sentiment}. Audience: {audience}.
Language: {language}. Detail level: {detail_level}.

Requirements:
- situation: factual description of what occurred/was reported
- impact: who/what is affected and how
- recommended_actions: concrete, actionable steps, not vague guidance
- severity: one of "low", "moderate", "high", "critical" — justified by the source, not inflated

Respond only with JSON matching the required schema — no markdown, no preamble."""


def build_system_instruction(params: dict) -> str:
    return SYSTEM_TEMPLATE.format(**params)
