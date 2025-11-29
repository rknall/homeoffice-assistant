"""Authentication service."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.models import SystemSettings, User
from src.models.enums import UserRole
from src.models.session import Session as SessionModel
from src.schemas.auth import RegisterRequest
from src.security import get_password_hash, verify_password

SESSION_EXPIRY_DAYS = 7


def is_first_run(db: Session) -> bool:
    """Check if this is the first run (no users exist)."""
    return db.query(User).count() == 0


def get_first_run_complete_setting(db: Session) -> bool:
    """Check if first_run_complete is set in system settings."""
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "first_run_complete"
    ).first()
    return setting is not None and setting.value == "true"


def set_first_run_complete(db: Session) -> None:
    """Mark first run as complete."""
    setting = SystemSettings(key="first_run_complete", value="true", is_encrypted=False)
    db.add(setting)
    db.commit()


def is_registration_enabled(db: Session) -> bool:
    """Check if user registration is enabled."""
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "registration_enabled"
    ).first()
    return setting is not None and setting.value == "true"


def register_user(db: Session, data: RegisterRequest) -> User:
    """Register a new user. First user becomes admin."""
    first_run = is_first_run(db)

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        role=UserRole.ADMIN if first_run else UserRole.USER,
        is_admin=first_run,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if first_run:
        set_first_run_complete(db)
        # Create default email template during first run
        from src.services import email_template_service
        email_template_service.ensure_default_template_exists(db)

    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Authenticate a user by username and password."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_session(db: Session, user_id: str) -> str:
    """Create a new session for a user."""
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRY_DAYS)

    session = SessionModel(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    return token


def get_session(db: Session, token: str) -> SessionModel | None:
    """Get a valid session by token."""
    session = db.query(SessionModel).filter(SessionModel.token == token).first()
    if not session:
        return None
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        return None
    return session


def delete_session(db: Session, token: str) -> bool:
    """Delete a session by token."""
    session = db.query(SessionModel).filter(SessionModel.token == token).first()
    if session:
        db.delete(session)
        db.commit()
        return True
    return False


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Get a user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def cleanup_expired_sessions(db: Session) -> int:
    """Delete all expired sessions. Returns count of deleted sessions."""
    count = db.query(SessionModel).filter(
        SessionModel.expires_at < datetime.utcnow()
    ).delete()
    db.commit()
    return count
