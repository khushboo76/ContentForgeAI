"""
Registry mapping an output_type string (as selected on the dashboard) to its
prompt-building module. Add a new output type by adding a module with
`build_system_instruction(params) -> str` and `SCHEMA` (JSON schema dict),
then registering it here — nothing else in the pipeline needs to change.
"""
from app.prompts import (
    linkedin_post,
    advisory,
    executive_summary,
    presentation,
    infographic,
    email,
)

REGISTRY = {
    "linkedin_post": linkedin_post,
    "advisory": advisory,
    "executive_summary": executive_summary,
    "presentation": presentation,
    "infographic": infographic,
    "email": email,
}


def get_template(output_type: str):
    if output_type not in REGISTRY:
        raise ValueError(
            f"Unknown output_type '{output_type}'. "
            f"Valid types: {', '.join(REGISTRY.keys())}"
        )
    return REGISTRY[output_type]
