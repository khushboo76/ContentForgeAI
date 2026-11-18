"""SQLAlchemy models for submission history, generated outputs, connected accounts, and publication records."""
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


class ConnectedAccount(Base):
    """Stores user-connected OAuth social accounts with tokens encrypted at rest."""
    __tablename__ = "connected_accounts"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False)  # "linkedin" | "gmail"
    account_id = Column(String, nullable=False)  # e.g. LinkedIn person URN or Google subject ID
    account_name = Column(String, nullable=False)  # User display name
    account_handle = Column(String, nullable=True)  # @handle or email
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class PublicationRecord(Base):
    """Audit log of direct publishing events to LinkedIn and email channels."""
    __tablename__ = "publication_records"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    output_id = Column(String, nullable=True)
    output_type = Column(String, nullable=True)
    channel = Column(String, nullable=False)  # "linkedin" | "gmail" | "email"
    status = Column(String, nullable=False)  # "published" | "failed"
    external_id = Column(String, nullable=True)  # Post ID or Email ID
    external_url = Column(String, nullable=True)  # Web link to the published post
    recipient = Column(String, nullable=True)  # Recipient email address(es)
    content_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
