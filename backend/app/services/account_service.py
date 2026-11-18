"""
Account management and publication auditing:
- Scoped strictly to authenticated/session user_id
- Encryption of tokens at rest using security module
- Audit logging of all publish events
"""
import datetime
from sqlalchemy.orm import Session
from app.models.db_models import ConnectedAccount, PublicationRecord
from app.core import security


def get_user_accounts(db: Session, user_id: str) -> list[ConnectedAccount]:
    """Returns all accounts connected by this specific user."""
    return db.query(ConnectedAccount).filter(ConnectedAccount.user_id == user_id).all()


def get_account_for_user(db: Session, user_id: str, account_id: str) -> ConnectedAccount | None:
    """Returns a specific connected account only if it belongs to this user."""
    return (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user_id, ConnectedAccount.id == account_id)
        .first()
    )


def save_or_update_account(
    db: Session,
    user_id: str,
    platform: str,
    account_id: str,
    account_name: str,
    account_handle: str | None,
    access_token: str,
    refresh_token: str | None = None,
    expires_in: int | None = None,
) -> ConnectedAccount:
    """Saves or updates an account with encrypted access/refresh tokens."""
    existing = (
        db.query(ConnectedAccount)
        .filter(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.platform == platform,
            ConnectedAccount.account_id == account_id,
        )
        .first()
    )

    expires_at = None
    if expires_in:
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

    encrypted_access = security.encrypt_token(access_token)
    encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None

    if existing:
        existing.account_name = account_name
        existing.account_handle = account_handle
        existing.encrypted_access_token = encrypted_access
        if encrypted_refresh:
            existing.encrypted_refresh_token = encrypted_refresh
        if expires_at:
            existing.expires_at = expires_at
        existing.updated_at = datetime.datetime.utcnow()
        account = existing
    else:
        account = ConnectedAccount(
            user_id=user_id,
            platform=platform,
            account_id=account_id,
            account_name=account_name,
            account_handle=account_handle,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            expires_at=expires_at,
        )
        db.add(account)

    db.commit()
    db.refresh(account)
    return account


def get_decrypted_tokens(account: ConnectedAccount) -> tuple[str, str | None]:
    """Safely decrypts access and refresh tokens for in-memory API calls."""
    access_token = security.decrypt_token(account.encrypted_access_token)
    refresh_token = security.decrypt_token(account.encrypted_refresh_token) if account.encrypted_refresh_token else None
    return access_token, refresh_token


def update_account_access_token(
    db: Session,
    account: ConnectedAccount,
    new_access_token: str,
) -> None:
    """Updates and re-encrypts the access token after a refresh."""
    account.encrypted_access_token = security.encrypt_token(new_access_token)
    account.updated_at = datetime.datetime.utcnow()
    db.commit()


def delete_user_account(db: Session, user_id: str, account_id: str) -> bool:
    """Deletes an account if it belongs to this user."""
    account = get_account_for_user(db, user_id, account_id)
    if not account:
        return False
    db.delete(account)
    db.commit()
    return True


def record_publication(
    db: Session,
    user_id: str,
    channel: str,
    status: str,
    output_id: str | None = None,
    output_type: str | None = None,
    external_id: str | None = None,
    external_url: str | None = None,
    recipient: str | None = None,
    content_summary: str | None = None,
    error_message: str | None = None,
) -> PublicationRecord:
    """Records an immutable audit entry for each publishing attempt."""
    record = PublicationRecord(
        user_id=user_id,
        output_id=output_id,
        output_type=output_type,
        channel=channel,
        status=status,
        external_id=external_id,
        external_url=external_url,
        recipient=recipient,
        content_summary=content_summary,
        error_message=error_message,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_user_publications(db: Session, user_id: str, limit: int = 30) -> list[PublicationRecord]:
    """Returns publication history for the user."""
    return (
        db.query(PublicationRecord)
        .filter(PublicationRecord.user_id == user_id)
        .order_by(PublicationRecord.created_at.desc())
        .limit(limit)
        .all()
    )

