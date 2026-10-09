"""SQLAlchemy models for submission history and generated outputs."""
import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=_uuid)
    source_content = Column(Text, nullable=False)
    params = Column(JSON, default=dict)  # tone/sentiment/audience/language/detail_level
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    outputs = relationship("GeneratedOutput", back_populates="submission", cascade="all, delete-orphan")


class GeneratedOutput(Base):
    __tablename__ = "generated_outputs"

    id = Column(String, primary_key=True, default=_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    output_type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # "done" | "failed"
    data = Column(JSON, nullable=True)        # structured result, if status == "done"
    error = Column(Text, nullable=True)       # error message, if status == "failed"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submission = relationship("Submission", back_populates="outputs")
