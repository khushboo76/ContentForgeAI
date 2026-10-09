"""
CRUD helpers for submission history — kept separate from routes.py so the
API layer stays thin and this logic is reusable/testable on its own.
"""
from sqlalchemy.orm import Session
from app.models.db_models import Submission, GeneratedOutput


def create_submission(db: Session, source_content: str, params: dict) -> Submission:
    submission = Submission(source_content=source_content, params=params)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def save_results(db: Session, submission_id: str, results: dict) -> None:
    for output_type, result in results.items():
        db.add(GeneratedOutput(
            submission_id=submission_id,
            output_type=output_type,
            status=result["status"],
            data=result.get("data"),
            error=result.get("error"),
        ))
    db.commit()


def list_submissions(db: Session, limit: int = 20) -> list[Submission]:
    return (
        db.query(Submission)
        .order_by(Submission.created_at.desc())
        .limit(limit)
        .all()
    )


def get_submission(db: Session, submission_id: str) -> Submission | None:
    return db.query(Submission).filter(Submission.id == submission_id).first()
