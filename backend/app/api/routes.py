import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.content_ingestion import ingest_text, ingest_file, ingest_url, ingest_media_file
from app.services.orchestrator import generate_all
from app.services import persistence
from app.prompts import REGISTRY

router = APIRouter()


class GenerationParams(BaseModel):
    tone: str | None = None
    sentiment: str | None = None
    audience: str | None = None
    language: str | None = None
    detail_level: str | None = None


class GenerateRequest(BaseModel):
    source_content: str          # pasted/typed text
    output_types: list[str]      # e.g. ["linkedin_post", "advisory"]
    params: GenerationParams | None = None


class UrlIngestRequest(BaseModel):
    url: str


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/output-types")
async def list_output_types():
    """Lets the frontend populate the OutputSelector without hardcoding types."""
    return {"output_types": list(REGISTRY.keys())}


@router.post("/generate")
async def generate_outputs(request: GenerateRequest, db: Session = Depends(get_db)):
    unknown = [t for t in request.output_types if t not in REGISTRY]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown output_types: {unknown}. Valid: {list(REGISTRY.keys())}",
        )
    if not request.output_types:
        raise HTTPException(status_code=400, detail="output_types cannot be empty")

    try:
        normalized = ingest_text(request.source_content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    params = request.params.model_dump(exclude_none=True) if request.params else {}

    submission = persistence.create_submission(db, normalized, params)
    results = await generate_all(normalized, request.output_types, params)
    persistence.save_results(db, submission.id, results)

    return {"submission_id": submission.id, "results": results}


@router.post("/ingest-file")
async def ingest_uploaded_file(file: UploadFile = File(...)):
    """
    Extracts text from an uploaded document (.txt/.md/.pdf/.docx) so the
    frontend can populate the source-content field before calling /generate.
    Kept separate from /generate so the dashboard can preview extracted text
    before committing to generation.
    """
    suffix = Path(file.filename or "").suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text = ingest_file(tmp_path)
    except NotImplementedError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"source_content": text}


@router.post("/ingest-url")
async def ingest_from_url(request: UrlIngestRequest):
    """
    Fetches a URL via Gemini's url_context tool and returns extracted text,
    so the frontend can populate the source-content field before calling
    /generate — same pattern as /ingest-file, just for links instead of
    uploaded documents.
    """
    try:
        text = await ingest_url(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # Gemini unavailable AND the local fetch fallback failed.
        raise HTTPException(status_code=502, detail=str(exc))

    return {"source_content": text}


@router.post("/generate-from-media")
async def generate_from_media(
    file: UploadFile = File(...),
    output_types: str = Form(...),   # JSON-encoded list, e.g. '["linkedin_post"]'
    params: str = Form("{}"),        # JSON-encoded GenerationParams dict
    db: Session = Depends(get_db),
):
    """
    Accepts an image or video directly as source content — no text
    extraction. The file is passed to Gemini as native multimodal input
    (see gemini_client.generate's media_parts param), alongside an optional
    text prompt/caption if the operator typed one into source_content-like
    context. Kept as a separate endpoint from /generate since the request
    shape (multipart file + form fields) differs from the JSON-only /generate.
    """
    try:
        output_types_list = json.loads(output_types)
        params_dict = json.loads(params)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in form field: {exc}")

    unknown = [t for t in output_types_list if t not in REGISTRY]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown output_types: {unknown}. Valid: {list(REGISTRY.keys())}",
        )
    if not output_types_list:
        raise HTTPException(status_code=400, detail="output_types cannot be empty")

    suffix = Path(file.filename or "").suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        media_bytes, mime_type = ingest_media_file(tmp_path)
    except NotImplementedError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    submission = persistence.create_submission(db, f"[media upload: {file.filename}]", params_dict)
    results = await generate_all(
        source_content="Analyze the attached image/video as the source content.",
        output_types=output_types_list,
        params=params_dict,
        media_parts=[(media_bytes, mime_type)],
    )
    persistence.save_results(db, submission.id, results)

    return {"submission_id": submission.id, "results": results}


@router.get("/submissions")
async def get_submissions(db: Session = Depends(get_db)):
    submissions = persistence.list_submissions(db)
    return {
        "submissions": [
            {"id": s.id, "source_content": s.source_content[:200], "created_at": s.created_at.isoformat()}
            for s in submissions
        ]
    }


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str, db: Session = Depends(get_db)):
    submission = persistence.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {
        "id": submission.id,
        "source_content": submission.source_content,
        "params": submission.params,
        "created_at": submission.created_at.isoformat(),
        "outputs": [
            {
                "output_type": o.output_type,
                "status": o.status,
                "data": o.data,
                "error": o.error,
            }
            for o in submission.outputs
        ],
    }
