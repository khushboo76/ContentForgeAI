// Human-readable labels for output types and generation control options.
// Keys must match the backend's app/prompts REGISTRY keys exactly.

export const OUTPUT_TYPE_LABELS: Record<string, string> = {
  linkedin_post: "LinkedIn Post",
  advisory: "Advisory",
  executive_summary: "Executive Summary",
  presentation: "Presentation",
  infographic: "Infographic",
  email: "Email Draft",
};

export const TONE_OPTIONS = [
  "formal",
  "urgent",
  "neutral-informative",
  "reassuring",
  "conversational",
];

export const SENTIMENT_OPTIONS = ["positive", "neutral", "cautionary", "critical"];

export const AUDIENCE_OPTIONS = [
  "general public",
  "technical staff",
  "executive leadership",
  "media",
];

export const DETAIL_LEVEL_OPTIONS = ["brief", "standard", "detailed"];

export const LANGUAGE_OPTIONS = ["English", "Hindi", "Spanish", "French"];
