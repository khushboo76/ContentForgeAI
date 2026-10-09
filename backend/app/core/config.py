import os
from dotenv import load_dotenv

load_dotenv()

# ---- Primary provider: Gemini ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
# How many times to retry Gemini on transient errors (429/500/502/503/504)
# before switching to a fallback provider. Keep low when a fallback is set,
# so a Gemini outage fails over in seconds instead of stalling the demo.
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "2"))

# ---- Fallback providers (OpenAI-compatible chat APIs, text-only) ----
# Tried in this order, skipping any whose API key is not set.
FALLBACK_ORDER = [
    name.strip().lower()
    for name in os.getenv("FALLBACK_ORDER", "mistral,groq").split(",")
    if name.strip()
]
FALLBACK_TIMEOUT_SECONDS = float(os.getenv("FALLBACK_TIMEOUT_SECONDS", "60"))

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Groq rotates its free-tier models; if this one is rejected, pick a current
# model from https://console.groq.com and set GROQ_MODEL in backend/.env.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# ---- Storage ----
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
