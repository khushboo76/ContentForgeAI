import json
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Header, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core import security
from app.services.content_ingestion import ingest_text, ingest_file, ingest_url, ingest_media_file
from app.services.orchestrator import generate_all
from app.services import persistence, account_service
from app.services.publishing import linkedin, gmail
from app.core import config
from app.prompts import REGISTRY

router = APIRouter()


def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    user_id: Optional[str] = Query(None, alias="user_id"),
) -> str:
    """Extracts or assigns an isolated user identifier to scope accounts and publishing."""
    uid = x_user_id or user_id
    if not uid or not uid.strip():
        return "default_operator"
    return uid.strip()


class GenerationParams(BaseModel):
    tone: Optional[str] = None
    sentiment: Optional[str] = None
    audience: Optional[str] = None
    language: Optional[str] = None
    detail_level: Optional[str] = None


class GenerateRequest(BaseModel):
    source_content: str          # pasted/typed text
    output_types: list[str]      # e.g. ["linkedin_post", "advisory"]
    params: Optional[GenerationParams] = None


class UrlIngestRequest(BaseModel):
    url: str


# ---- Publishing Request Schemas ----
class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class PublishLinkedInRequest(BaseModel):
    account_id: str
    text: str
    output_id: Optional[str] = None
    output_type: Optional[str] = "linkedin_post"


class SendEmailRequest(BaseModel):
    account_id: str
    recipients: List[str]
    subject: str
    body_text: str
    body_html: Optional[str] = None
    output_id: Optional[str] = None
    output_type: Optional[str] = None


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
    try:
        text = await ingest_url(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"source_content": text}


@router.post("/generate-from-media")
async def generate_from_media(
    file: UploadFile = File(...),
    output_types: str = Form(...),   # JSON-encoded list, e.g. '["linkedin_post"]'
    params: str = Form("{}"),        # JSON-encoded GenerationParams dict
    db: Session = Depends(get_db),
):
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


# ============================================================================
# OAuth & Connected Accounts (Scoped to Authenticated/Session User)
# ============================================================================

@router.get("/auth/{platform}/authorize-url")
async def get_authorization_url(
    platform: str,
    user_id: str = Depends(get_current_user_id),
):
    """Generates a protected OAuth authorization URL for a supported provider."""
    if platform == "linkedin":
        state = security.create_oauth_state(user_id=user_id, platform="linkedin")
        url, is_cfg = linkedin.build_authorization_url(state)
        return {
            "authorization_url": url,
            "state": state,
            "platform": "linkedin",
            "is_configured": is_cfg,
        }
    elif platform in ("gmail", "google"):
        state = security.create_oauth_state(user_id=user_id, platform="gmail")
        url, is_cfg = gmail.build_authorization_url(state)
        return {
            "authorization_url": url,
            "state": state,
            "platform": "gmail",
            "is_configured": is_cfg,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


@router.get("/auth/{platform}/callback")
async def oauth_callback_get(
    platform: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Completes a browser OAuth redirect and returns the user to the dashboard."""
    try:
        if error:
            raise ValueError(f"Google authorization was not completed: {error}")
        if not code or not state:
            raise ValueError("Google authorization response is missing code or state")
        state_data = security.verify_oauth_state(state)
        if state_data["platform"] != platform and not (platform == "google" and state_data["platform"] == "gmail"):
            raise ValueError("OAuth platform mismatch")
        user_id = state_data["user_id"]
        if platform == "linkedin":
            tokens = await linkedin.exchange_code_for_token(code)
            profile = await linkedin.fetch_user_profile(tokens["access_token"])
            account_service.save_or_update_account(
                db=db,
                user_id=user_id,
                platform="linkedin",
                account_id=profile["sub"],
                account_name=profile.get("name", "LinkedIn Member"),
                account_handle=profile.get("email"),
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                expires_in=tokens.get("expires_in"),
            )
        elif platform in ("gmail", "google"):
            tokens = await gmail.exchange_code_for_token(code)
            profile = await gmail.fetch_user_profile(tokens["access_token"])
            account_service.save_or_update_account(
                db=db,
                user_id=user_id,
                platform="gmail",
                account_id=profile.get("sub") or profile.get("email"),
                account_name=profile.get("name", "Gmail User"),
                account_handle=profile.get("email"),
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                expires_in=tokens.get("expires_in"),
            )
        else:
            raise ValueError("Unsupported platform")
    except Exception as exc:
        return RedirectResponse(f"{config.FRONTEND_URL}/dashboard?{urlencode({'oauth_error': str(exc)})}")

    return RedirectResponse(f"{config.FRONTEND_URL}/dashboard?{urlencode({'connected': platform})}")


@router.post("/auth/{platform}/callback")
async def oauth_callback(
    platform: str,
    payload: OAuthCallbackRequest,
    db: Session = Depends(get_db),
):
    """Validates the state and exchanges authorization code for encrypted tokens."""
    try:
        state_data = security.verify_oauth_state(payload.state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user_id = state_data["user_id"]
    if state_data["platform"] != platform and not (platform == "google" and state_data["platform"] == "gmail"):
        raise HTTPException(status_code=400, detail="OAuth platform mismatch")

    if platform == "linkedin":
        try:
            tokens = await linkedin.exchange_code_for_token(payload.code)
            profile = await linkedin.fetch_user_profile(tokens["access_token"])
            account = account_service.save_or_update_account(
                db=db,
                user_id=user_id,
                platform="linkedin",
                account_id=profile["sub"],
                account_name=profile.get("name", "LinkedIn Member"),
                account_handle=profile.get("email"),
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                expires_in=tokens.get("expires_in"),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"LinkedIn authentication failed: {exc}")

    elif platform in ("gmail", "google"):
        try:
            tokens = await gmail.exchange_code_for_token(payload.code)
            profile = await gmail.fetch_user_profile(tokens["access_token"])
            account = account_service.save_or_update_account(
                db=db,
                user_id=user_id,
                platform="gmail",
                account_id=profile.get("sub") or profile.get("email"),
                account_name=profile.get("name", "Gmail User"),
                account_handle=profile.get("email"),
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                expires_in=tokens.get("expires_in"),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Gmail authentication failed: {exc}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    return {
        "status": "connected",
        "account": {
            "id": account.id,
            "platform": account.platform,
            "account_name": account.account_name,
            "account_handle": account.account_handle,
            "created_at": account.created_at.isoformat(),
        },
    }


@router.get("/accounts")
async def list_connected_accounts(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Returns all accounts connected by this user. Tokens are never exposed."""
    accounts = account_service.get_user_accounts(db, user_id)
    return {
        "accounts": [
            {
                "id": acc.id,
                "platform": acc.platform,
                "account_name": acc.account_name,
                "account_handle": acc.account_handle,
                "created_at": acc.created_at.isoformat(),
            }
            for acc in accounts
        ]
    }


@router.delete("/accounts/{account_id}")
async def delete_connected_account(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Disconnects and securely revokes an account for this user."""
    success = account_service.delete_user_account(db, user_id, account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connected account not found")
    return {"status": "deleted", "account_id": account_id}


# ============================================================================
# Direct Publishing: LinkedIn and Email
# ============================================================================

@router.post("/publish/linkedin")
async def publish_to_linkedin(
    request: PublishLinkedInRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    account = account_service.get_account_for_user(db, user_id, request.account_id)
    if not account or account.platform != "linkedin":
        raise HTTPException(status_code=404, detail="LinkedIn account not connected for this user")

    access_token, _ = account_service.get_decrypted_tokens(account)
    try:
        result = await linkedin.publish_post(access_token, account.account_id, request.text)
        account_service.record_publication(
            db=db,
            user_id=user_id,
            channel="linkedin",
            status="published",
            output_id=request.output_id,
            output_type=request.output_type,
            external_id=result.get("id"),
            external_url=result.get("url"),
            content_summary=request.text[:120],
        )
        return {
            "status": "published",
            "platform": "linkedin",
            "post_id": result.get("id"),
            "url": result.get("url"),
            "mode": result.get("mode", "live"),
        }
    except Exception as exc:
        account_service.record_publication(
            db=db,
            user_id=user_id,
            channel="linkedin",
            status="failed",
            output_id=request.output_id,
            output_type=request.output_type,
            content_summary=request.text[:120],
            error_message=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Failed to publish to LinkedIn: {exc}")


@router.post("/publish/email")
async def send_deliverable_email(
    request: SendEmailRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Sends a deliverable through the authenticated user's Gmail account."""
    html_content = request.body_html
    if not html_content:
        # Wrap plaintext in formatted email container
        escaped_lines = "<br>".join(line for line in request.body_text.splitlines())
        html_content = f"""
        <div style="font-family:sans-serif;line-height:1.6;color:#111827;padding:16px;">
            <p>{escaped_lines}</p>
        </div>
        """

    account = account_service.get_account_for_user(db, user_id, request.account_id)
    if not account or account.platform != "gmail":
        raise HTTPException(status_code=404, detail="Connect and select a Gmail account before sending email")

    access_token, refresh_token = account_service.get_decrypted_tokens(account)
    sender_email = account.account_handle or "me"
    try:
        result, new_access_token = await gmail.send_gmail_message(
            access_token=access_token,
            refresh_token=refresh_token,
            sender_email=sender_email,
            recipients=request.recipients,
            subject=request.subject,
            body_text=request.body_text,
            body_html=html_content,
        )
        if new_access_token:
            account_service.update_account_access_token(db, account, new_access_token)

        account_service.record_publication(
            db=db,
            user_id=user_id,
            channel="gmail",
            status="published",
            output_id=request.output_id,
            output_type=request.output_type,
            external_id=result.get("id"),
            recipient=", ".join(request.recipients),
            content_summary=f"[{request.subject}] {request.body_text[:80]}",
        )
        return {
            "status": "sent",
            "channel": "gmail",
            "id": result.get("id"),
            "threadId": result.get("threadId"),
            "recipients": request.recipients,
            "subject": request.subject,
            "sender": sender_email,
            "mode": result.get("mode", "live"),
        }
    except Exception as exc:
        account_service.record_publication(
            db=db,
            user_id=user_id,
            channel="gmail",
            status="failed",
            output_id=request.output_id,
            output_type=request.output_type,
            recipient=", ".join(request.recipients),
            content_summary=f"[{request.subject}] {request.body_text[:80]}",
            error_message=str(exc),
        )
        error_text = str(exc)
        if "invalid_grant" in error_text.lower() or "expired or revoked" in error_text.lower():
            raise HTTPException(
                status_code=401,
                detail="Your Gmail connection has expired or was revoked. Reconnect Gmail, then send again.",
            )
        raise HTTPException(status_code=502, detail=f"Failed to send email via Gmail API: {exc}")


@router.get("/publish/history")
async def get_publication_history(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Retrieves the publication log for this user."""
    records = account_service.get_user_publications(db, user_id)
    return {
        "publications": [
            {
                "id": r.id,
                "channel": r.channel,
                "status": r.status,
                "output_type": r.output_type,
                "external_id": r.external_id,
                "external_url": r.external_url,
                "recipient": r.recipient,
                "content_summary": r.content_summary,
                "error_message": r.error_message,
                "published_at": r.created_at.isoformat(),
            }
            for r in records
        ]
    }
