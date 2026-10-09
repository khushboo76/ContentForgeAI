# Architecture Document (draft placeholder — expand to 2 pages)

## Components
- Frontend (Next.js dashboard)
- Backend API (FastAPI)
- Prompt Template Registry
- Gemini Orchestrator (batching, retry/backoff)
- Gemini API (Flash / Flash-Lite)
- Storage (SQLite/Postgres for history)

## Data Flow
1. Operator submits source content + selects output types + sets generation params
2. `POST /api/generate` receives `{source_content, output_types, params}`
3. `content_ingestion.ingest_text` normalizes the source
4. `orchestrator.generate_all` loops sequentially over selected output types
   (sequential by design — respects the free-tier RPM limit rather than
   firing concurrent requests into a 429 storm)
5. For each type, `prompts.get_template` returns its system instruction +
   JSON schema; `gemini_client.generate` calls the API with structured output
6. `retry.with_backoff` wraps every Gemini call — retries up to 4 times on
   429/RESOURCE_EXHAUSTED with exponential backoff + jitter (1s → 2s → 4s → 8s)
7. Optional: `tone_validator.validate_tone` scores the result against the
   requested tone/sentiment (1-5) via a second Gemini call
8. Response returns `{ output_type: {status, data|error} }` — partial
   failures on one output type don't block the others
9. Frontend renders each deliverable in its preview panel

## Implemented vs. Stub
- **Implemented**: gemini_client, retry/backoff, orchestrator, all 7 prompt
  templates + schemas, /generate and /output-types routes, tone_validator
- **Stub (extend as needed)**: file-based ingestion beyond .txt/.md,
  db persistence (submission history), frontend components/pages

## Resilience & Fallback
- `gemini_client._raise_if_transient` classifies 429/500/502/503/504, timeouts, and
  "UNAVAILABLE"/"high demand" messages as transient (`RateLimitError`); other errors
  (bad request, auth) are never retried or masked.
- `@with_backoff` retries transient errors (`GEMINI_MAX_RETRIES`, default 2).
- `gemini_client.generate()` then fails over to `llm_fallback.generate_json()`
  (Mistral -> Groq via OpenAI-compatible chat APIs). The JSON schema is added to the
  prompt, replies are parsed defensively, and required keys are verified.
- `gemini_client.extract_url_text()` falls back to `url_fetcher.fetch_url_text()`,
  which blocks private/internal addresses (SSRF protection).
- Media (image/video) requests and infographic image generation are Gemini-only.
