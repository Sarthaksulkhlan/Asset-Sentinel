import hashlib
import secrets
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, cast
from uuid import uuid4

import bcrypt
import jwt
from flask import g, jsonify, request
from sqlalchemy import func, or_, select, text

from config import Config
from database import get_db_session
from models import RefreshToken, User


ROLE_SUPER_ADMIN = "Super Admin"
ROLE_ADMIN = "Admin"
ROLE_IT_ADMIN = "IT Admin"
ROLE_VIEWER = "Viewer"
VALID_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_IT_ADMIN, ROLE_VIEWER}
F = TypeVar("F", bound=Callable[..., Any])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_id(user: User) -> int:
    return int(cast(Any, user.id))


def _as_str(value: Any) -> str:
    return str(cast(Any, value) or "")


def _as_optional_str(value: Any) -> Optional[str]:
    raw = cast(Any, value)
    return str(raw) if raw not in (None, "") else None


def _as_bool(value: Any) -> bool:
    return bool(cast(Any, value))


def _refresh_expires_at(token_row: RefreshToken) -> datetime:
    return cast(datetime, cast(Any, token_row.expires_at))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def serialize_user(user: User) -> Dict[str, Any]:
    username = _as_str(user.username)
    return {
        "id": _user_id(user),
        "email": _as_str(user.email),
        "username": username,
        "displayName": _as_optional_str(user.display_name) or username,
        "role": _as_str(user.role),
        "externalProvider": _as_optional_str(user.external_provider),
    }


def create_access_token(user: User) -> str:
    issued_at = _now()
    expires_at = issued_at + Config.JWT_ACCESS_TOKEN_EXPIRES
    payload = {
        "iss": Config.JWT_ISSUER,
        "aud": Config.JWT_AUDIENCE,
        "sub": str(_user_id(user)),
        "username": _as_str(user.username),
        "email": _as_str(user.email),
        "role": _as_str(user.role),
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(user: User) -> str:
    issued_at = _now()
    expires_at = issued_at + Config.JWT_REFRESH_TOKEN_EXPIRES
    jwt_id = str(uuid4())
    nonce = secrets.token_urlsafe(16)
    payload = {
        "iss": Config.JWT_ISSUER,
        "aud": Config.JWT_AUDIENCE,
        "sub": str(_user_id(user)),
        "type": "refresh",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jwt_id,
        "nonce": nonce,
    }
    token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
    with get_db_session() as session:
        session.add(
            RefreshToken(
                user_id=_user_id(user),
                token_hash=_hash_token(token),
                jwt_id=jwt_id,
                expires_at=expires_at,
            )
        )
    return token


def decode_token(token: str, expected_type: str) -> Dict[str, Any]:
    payload = jwt.decode(
        token,
        Config.JWT_SECRET_KEY,
        algorithms=["HS256"],
        audience=Config.JWT_AUDIENCE,
        issuer=Config.JWT_ISSUER,
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


class LocalIdentityProvider:
    name = "local"

    def authenticate(self, identifier: str, password: str) -> Optional[User]:
        normalized = (identifier or "").strip().lower()
        if not normalized:
            return None
        with get_db_session() as session:
            user = session.execute(
                select(User).where(
                    or_(func.lower(User.username) == normalized, func.lower(User.email) == normalized),
                    User.is_active.is_(True),
                ).limit(1)
            ).scalar_one_or_none()
            if user and verify_password(password, _as_optional_str(user.password_hash)):
                user.last_login_at = _now()
                session.flush()
                session.expunge(user)
                return user
        return None


def issue_token_pair(user: User) -> Dict[str, Any]:
    return {
        "accessToken": create_access_token(user),
        "refreshToken": create_refresh_token(user),
        "tokenType": "Bearer",
        "expiresIn": int(Config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
        "user": serialize_user(user),
    }


def authenticate_local(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    provider = LocalIdentityProvider()
    user = provider.authenticate(identifier, password)
    if not user:
        return None
    return issue_token_pair(user)


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    payload = decode_token(refresh_token, "refresh")
    token_hash = _hash_token(refresh_token)
    with get_db_session() as session:
        token_row = session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.jwt_id == payload.get("jti"))
            .where(RefreshToken.revoked_at.is_(None))
            .limit(1)
        ).scalar_one_or_none()
        if not token_row or _refresh_expires_at(token_row) < _now():
            return None
        user = session.get(User, int(payload["sub"]))
        if not user or not _as_bool(user.is_active):
            return None
        return {
            "accessToken": create_access_token(user),
            "tokenType": "Bearer",
            "expiresIn": int(Config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
            "user": serialize_user(user),
        }


def revoke_refresh_token(refresh_token: str) -> bool:
    try:
        payload = decode_token(refresh_token, "refresh")
    except jwt.PyJWTError:
        return False
    token_hash = _hash_token(refresh_token)
    with get_db_session() as session:
        token_row = session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.jwt_id == payload.get("jti"))
            .where(RefreshToken.revoked_at.is_(None))
            .limit(1)
        ).scalar_one_or_none()
        if not token_row:
            return False
        token_row.revoked_at = _now()
        return True


def current_user_from_request() -> Tuple[Optional[User], Optional[str]]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, "Missing bearer token"
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, "access")
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.PyJWTError:
        return None, "Invalid token"

    with get_db_session() as session:
        user = session.get(User, int(payload["sub"]))
        if not user or not _as_bool(user.is_active):
            return None, "User is inactive"
        session.expunge(user)
        return user, None


def require_auth(required_roles: Optional[set[str]] = None) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)
            user, error = current_user_from_request()
            if error or not user:
                return jsonify({"error": "Unauthorized", "detail": error or "Authentication required"}), 401
            if required_roles and _as_str(user.role) not in required_roles:
                return jsonify({"error": "Forbidden", "detail": "Insufficient permissions"}), 403
            g.current_user = user
            return fn(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def ensure_auth_schema() -> None:
    """
    Bring pre-JWT installations in line with the current auth model.

    SQLAlchemy create_all() creates missing tables but does not alter existing
    check constraints, so older databases can still reject the current role
    values. Keep this in sync with auth_login_activity_migration.sql.
    """
    with get_db_session() as session:
        session.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS login_source VARCHAR(50)"))
        session.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS windows_event_id VARCHAR(20)"))
        session.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS windows_event_record_id VARCHAR(255)"))
        session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_sessions_windows_event_record_id "
            "ON sessions (windows_event_record_id)"
        ))
        session.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role"))
        session.execute(text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'Admin'"))
        session.execute(text(
            """
            UPDATE users
            SET role = CASE lower(role)
                WHEN 'super_admin' THEN 'Super Admin'
                WHEN 'super admin' THEN 'Super Admin'
                WHEN 'admin' THEN 'Admin'
                WHEN 'analyst' THEN 'IT Admin'
                WHEN 'it admin' THEN 'IT Admin'
                WHEN 'viewer' THEN 'Viewer'
                ELSE 'Viewer'
            END
            """
        ))
        session.execute(text(
            "ALTER TABLE users "
            "ADD CONSTRAINT chk_users_role "
            "CHECK (role IN ('Super Admin', 'Admin', 'IT Admin', 'Viewer'))"
        ))
        session.execute(text(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash VARCHAR(128) NOT NULL,
                jwt_id VARCHAR(255) NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash),
                CONSTRAINT uq_refresh_tokens_jwt_id UNIQUE (jwt_id)
            )
            """
        ))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens (user_id)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens (expires_at)"))


def bootstrap_admin_user() -> None:
    username = Config.BOOTSTRAP_ADMIN_USERNAME
    password = Config.BOOTSTRAP_ADMIN_PASSWORD
    email = Config.BOOTSTRAP_ADMIN_EMAIL
    if not username or not password or not email:
        print("[AUTH] Bootstrap admin is not configured; skipping admin bootstrap.")
        return
    with get_db_session() as session:
        existing = session.execute(
            select(User)
            .where(or_(func.lower(User.username) == username.lower(), func.lower(User.email) == email.lower()))
            .limit(1)
        ).scalar_one_or_none()
        if existing:
            existing.email = email
            existing.username = username
            existing.display_name = Config.BOOTSTRAP_ADMIN_DISPLAY_NAME
            existing.role = ROLE_SUPER_ADMIN
            existing.is_active = True
            existing.external_provider = existing.external_provider or "local"
            existing.external_subject = existing.external_subject or username
            if not existing.password_hash:
                existing.password_hash = hash_password(password)
            print(f"[AUTH] Bootstrap admin ready: username={username}, email={email}")
            return

        session.add(
            User(
                username=username,
                email=email,
                display_name=Config.BOOTSTRAP_ADMIN_DISPLAY_NAME,
                password_hash=hash_password(password),
                role=ROLE_SUPER_ADMIN,
                is_active=True,
                external_provider="local",
                external_subject=username,
            )
        )
        print(f"[AUTH] Bootstrap admin created: username={username}, email={email}")
