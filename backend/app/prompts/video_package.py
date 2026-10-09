from app.schemas.output_schemas import VideoPackageOutput

SCHEMA = VideoPackageOutput.model_json_schema()

SYSTEM_TEMPLATE = """You are producing a complete short-video content package from the
source below. You are NOT generating an actual video — only the script, storyboard,
narration, and subtitle text a production team would use.

Tone: {tone}. Sentiment: {sentiment}. Audience: {audience}.
Language: {language}. Detail level: {detail_level}.

Requirements:
- script: full narration script, scene breaks marked clearly
- storyboard: ordered list of scenes, each with scene_number, a visual description,
  the narration line for that scene, and a subtitle (may match narration, trimmed
  to subtitle-appropriate length)
- visual_recommendations: overall visual style, pacing, and any on-screen text guidance

Respond only with JSON matching the required schema — no markdown, no preamble."""


def build_system_instruction(params: dict) -> str:
    return SYSTEM_TEMPLATE.format(**params)
