import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.User import User, UserSession


PASSWORD_ITERATIONS = 600_000
SESSION_DAYS = 7


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"{PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        iterations, salt_hex, expected_hex = stored_hash.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), expected_hex)


def identifier_type(identifier: str) -> str:
    return "email" if "@" in identifier else "phone"


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    )
    db.add(session)
    db.commit()
    return token


def find_session_user(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.execute(
        select(UserSession).where(UserSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if session is None or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return None
    return db.get(User, session.user_id)


def delete_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.execute(
        select(UserSession).where(UserSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if session is not None:
        db.delete(session)
        db.commit()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
