# AI Content Transformation Platform

Converts a single source of content (text, document, image, video, or free-form prompt)
into multiple operator-selected deliverables: LinkedIn posts, advisories,
executive summaries, presentations, infographic content, and video packages (script,
storyboard, narration, subtitles).

## Structure

- `frontend/` — Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui dashboard
- `backend/` — FastAPI service: content ingestion, prompt template registry, Gemini
  orchestration, tone/sentiment validation
- `docs/` — Architecture document and PRD

## Setup

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # add your GEMINI_API_KEY
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:3000, backend on http://localhost:8000.

## Configuration (`backend/.env`)

Copy `.env.example` to `backend/.env` and fill in:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Primary provider — required |
| `GEMINI_MODEL` / `GEMINI_IMAGE_MODEL` | Text model / infographic image model |
| `MISTRAL_API_KEY`, `GROQ_API_KEY` | Fallback providers — set at least one |
| `FALLBACK_ORDER` | Order fallbacks are tried (default `mistral,groq`) |
| `GEMINI_MAX_RETRIES` | Gemini retries before failing over (default 2) |

## Resilience

Gemini's free tier regularly returns `503 UNAVAILABLE` ("high demand") or `429`.
Transient errors are retried with exponential backoff; if Gemini is still down,
text generation fails over to Mistral/Groq and URL ingestion falls back to a
direct page fetch. Image/video inputs and infographic images are Gemini-only.
