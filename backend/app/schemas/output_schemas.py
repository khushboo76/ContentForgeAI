# Pydantic schemas defining the structured JSON shape expected back
# from Gemini for each output type (used with response_mime_type=application/json).
from pydantic import BaseModel
from typing import List, Optional


class LinkedInPostOutput(BaseModel):
    hook: str
    body: str
    hashtags: List[str]
    cta: Optional[str] = None


class AdvisoryOutput(BaseModel):
    situation: str
    impact: str
    recommended_actions: List[str]
    severity: str


class ExecutiveSummaryOutput(BaseModel):
    summary: str
    key_findings: List[str]
    recommendations: List[str]


class PresentationSlide(BaseModel):
    title: str
    bullets: List[str]
    speaker_notes: str


class PresentationOutput(BaseModel):
    slides: List[PresentationSlide]


class InfographicOutput(BaseModel):
    key_messages: List[str]
    sections: List[str]
    layout_recommendations: str


class EmailOutput(BaseModel):
    subject: str
    body: str
    key_points: List[str]
    call_to_action: Optional[str] = None
