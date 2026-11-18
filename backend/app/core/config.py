import os
from dotenv import load_dotenv

load_dotenv()

# ---- Primary provider: Gemini ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
# How many times to retry Gemini on transient errors (429/500/502/503/504)
# before switching to a fallback provider.
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "2"))

# ---- Fallback providers (OpenAI-compatible chat APIs, text-only) ----
FALLBACK_ORDER = [
    name.strip().lower()
    for name in os.getenv("FALLBACK_ORDER", "groq").split(",")
    if name.strip()
]
FALLBACK_TIMEOUT_SECONDS = float(os.getenv("FALLBACK_TIMEOUT_SECONDS", "60"))

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# ---- Storage ----
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# ---- Security & Token Encryption ----
SECRET_KEY = os.getenv("SECRET_KEY", "content-transformer-secure-secret-key-salt")
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")

# ---- LinkedIn OAuth ----
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/auth/linkedin/callback")
# LinkedIn version headers use YYYYMM. Keep this on a currently supported
# version; obsolete releases are rejected with NONEXISTENT_VERSION (426).
LINKEDIN_API_VERSION = os.getenv("LINKEDIN_API_VERSION", "202610")

# ---- Google / Gmail OAuth 2.0 ----
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/gmail/callback")

# ---- Application URLs ----
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
