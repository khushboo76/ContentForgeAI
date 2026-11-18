# Product Requirements Document
## AI-Powered Content Transformation Engine

**Version:** 1.0
**Status:** Draft for build

---

## 1. Overview

Organisations regularly need to convert a single piece of source content — a report, advisory, article, incident summary, or free-form prompt — into multiple communication-ready deliverables (social posts, executive briefings, video scripts, presentations, advisories). Doing this manually is slow, inconsistent, and requires content, communication, and domain expertise.

This platform is an AI-powered content transformation engine: an operator submits source content once, selects one or more desired output formats and generation parameters, and the system produces publication-ready deliverables for each selected format from that single source.

## 2. Goals

- Reduce manual content-repurposing effort from hours to minutes
- Ensure consistent messaging across every output format generated from the same source
- Give operators fine-grained control over tone, sentiment, audience, language, and detail level without needing to re-prompt manually
- Support generating multiple deliverables in parallel from one submission

## 3. Target Users

- Communications/PR teams repurposing reports into social content
- Security/threat-intel teams turning incident data into advisories
- Policy teams converting research into briefings and public-facing summaries
- Any operator who needs one source turned into several channel-specific artefacts

## 4. Scope

**In scope (MVP):**
- Text generation for all listed output types (see §6.2) — including text *packages* for video (script, storyboard, scene descriptions, narration, subtitles) and infographics (content + layout recommendations), not rendered media
- Multi-select output generation from one submission
- Tone, sentiment, audience, language, and detail-level controls
- Structured, exportable output per format

**Out of scope (MVP):**
- Actual video rendering/editing
- Actual infographic/image rendering (design tool integration is a stretch goal)
- Multi-user roles/permissions, billing, analytics dashboards

## 5. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | Operator can submit source content as text, pasted text, or an uploaded document/image/video via the dashboard |
| FR-2 | Operator can select one or more output types via configurable checkboxes: Video Package, LinkedIn Post, Advisory, Infographic Content, Executive Summary, Presentation |
| FR-3 | Operator can configure generation parameters: tone, sentiment, target audience, language, level of detail, communication objective |
| FR-4 | System analyzes source content once and reuses that understanding across all selected output types (single context, multiple generations) |
| FR-5 | System generates one structured deliverable per selected output type, each following a format-specific schema |
| FR-6 | Operator can view, edit, regenerate, and export each generated deliverable independently |
| FR-7 | System validates generated tone/sentiment against the requested configuration and flags mismatches |
| FR-8 | System handles rate-limit/API failures gracefully with retry and clear operator-facing status |

## 6. Feature Details

### 6.1 Dashboard & Content Submission
Single-page submission flow: paste/upload source content → preview extracted content → proceed to configuration.

### 6.2 Output Type Selection
Multi-select cards, each mapped to a distinct prompt template and JSON output schema:

- **Video Package** → script, storyboard, scene-by-scene descriptions, narration text, subtitles, visual recommendations
- **LinkedIn Post** → publication-ready post with hook, body, hashtags, suggested CTA
- **Advisory** → structured advisory (situation, impact, recommended actions, severity)
- **Infographic** → key messages, section breakdown, layout/visual-hierarchy recommendations
- **Executive Summary** → concise briefing with key findings and recommendations
- **Presentation** → slide-by-slide content with speaker notes

### 6.3 Generation Controls
Dropdown/slider parameters, injected into every prompt template as system-level constraints:
- **Tone**: formal, urgent, neutral-informative, reassuring, conversational
- **Sentiment**: positive, neutral/factual, cautionary, critical
- **Audience**: general public, technical staff, executive leadership, media
- **Language**: configurable (English default)
- **Detail level**: brief / standard / detailed

### 6.4 Multi-Output Generation
Selected output types are generated from the same analyzed source in a batched/queued sequence (not one giant call) to respect free-tier rate limits, with progress shown per deliverable.

### 6.5 Output Rendering & Export
Each output renders in a format-appropriate preview (e.g. social-post card, slide list, advisory document) with copy/download/export actions.

## 7. Non-Functional Requirements

- **Performance**: individual deliverable generation should complete within ~10–15s under normal free-tier latency
- **Reliability**: exponential backoff + retry on 429/5xx from the LLM API
- **Privacy**: source content may include sensitive material (incident reports, threat intel) — flag to operators that free-tier LLM usage may be used for model training; recommend a paid/Vertex tier for sensitive deployments
- **Extensibility**: adding a new output type should only require a new prompt template + schema, no core changes
- **Consistency**: all outputs from one submission must reflect the same source understanding (no contradicting facts across formats)

## 8. System Architecture (Summary)

```
Dashboard (frontend)
   → Backend API
        → Content ingestion & preprocessing (text extraction, multimodal parsing)
        → Prompt Template Registry (one template + JSON schema per output type)
        → LLM Orchestrator (batches calls, applies tone/sentiment params, handles retries)
        → Gemini API (Flash / Flash-Lite, free tier)
        → Structured JSON response per output type
   → Frontend renders per-type deliverable views
```

A full architecture diagram belongs in the separate 2-page Architecture Document deliverable.

## 9. Recommended Tech Stack

**Frontend — clean, modern dashboard UI:**
- **Next.js (App Router) + TypeScript** — fast to build, good defaults, easy deployment
- **Tailwind CSS** — utility-first styling for a clean, consistent visual system
- **shadcn/ui** — accessible, minimal, easily themeable components (cards, dropdowns, tabs, dialogs) that read as modern SaaS rather than templated
- **Framer Motion** — subtle micro-interactions (loading states per deliverable, panel transitions) without overdoing it
- Design direction: generous whitespace, one accent color, soft elevation/shadow rather than heavy borders, clear per-output-type cards with status indicators (queued/generating/done)

**Backend:**
- **Python + FastAPI** — matches a Python/ML-leaning stack, straightforward to extend later with actual ML components (e.g. tone-validation scoring, embeddings for source analysis)
- Async request handling for batched multi-output generation

**LLM Layer:**
- Gemini API (Flash for main generation, Flash-Lite as fallback under rate pressure)
- Structured output via `response_mime_type: application/json` with per-output-type schemas

**Storage:**
- Lightweight — SQLite/Postgres for submission history and generated outputs; local/object storage for uploaded source files

## 10. Prompt Engineering Approach

- One system-instruction template per output type, parameterized with tone/sentiment/audience/language/detail
- Few-shot examples embedded per template where available, for reliable style matching
- Explicit vocabulary constraints for sensitive domains (advisories) to avoid speculative or alarmist language
- Optional second-pass validation call: score generated output against requested tone/sentiment (1–5), auto-regenerate below threshold

## 11. Constraints & Risks

- Free-tier rate limits (~15 RPM / ~1,000–1,500 RPD on Flash-Lite/Flash) — mitigate with request batching, backoff, and queuing in the demo
- Free-tier data usage terms mean sensitive source content shouldn't be used as-is without disclosure or a paid-tier upgrade path
- No native video/infographic rendering — output is the structured content package, not final rendered media (matches spec's literal wording)
- Multimodal input (image/video as source) needs file-size/type validation before hitting the API

## 12. Success Metrics

- Time from submission to first deliverable rendered
- Number of output types successfully generated per submission without manual correction
- Tone/sentiment match rate (validation pass rate)
- Operator edit rate post-generation (lower = better first-pass quality)

## 13. Deliverables Mapping (for evaluation)

| Deliverable | Maps to |
|-------------|---------|
| Source Code | Frontend (Next.js) + Backend (FastAPI) + prompt template registry |
| README | Setup instructions for API key, environment, running frontend/backend |
| Architecture Document (≤2 pages) | Diagram from §8, expanded with data flow and schema examples |
| Demo Video (≤2 min) | One submission → 2–3 output types generated live |
| Technical Presentation (≤5 slides) | Problem → Architecture → Tech stack → Demo screenshot → Roadmap |

## 14. Suggested Build Order

1. Backend: single output-type generation (e.g. LinkedIn Post) end-to-end with Gemini
2. Add remaining output-type templates + schemas
3. Frontend dashboard: submission + output-type multi-select
4. Generation controls (tone/sentiment/audience/language/detail)
5. Batched multi-output generation + status UI
6. Polish: export, regenerate, tone-validation pass
