import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, cast
from uuid import uuid4

import bcrypt
import jwt
from flask import g, jsonify, request
from sqlalchemy import desc, func, or_, select, text, update

from config import Config
from database import get_db_session
from models import AdminUser, Company, PasswordResetOtp, RefreshToken, User
from notifications import get_last_email_error, send_password_reset_otp_email


ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_COMPANY_ADMIN = "COMPANY_ADMIN"
ROLE_LEGACY_SUPER_ADMIN = "Super Admin"
ROLE_ADMIN = "Admin"
ROLE_IT_ADMIN = "IT Admin"
ROLE_VIEWER = "Viewer"
VALID_ROLES = {ROLE_SUPER_ADMIN, ROLE_COMPANY_ADMIN, ROLE_LEGACY_SUPER_ADMIN, ROLE_ADMIN, ROLE_IT_ADMIN, ROLE_VIEWER}
ROLE_ALIASES = {
    ROLE_LEGACY_SUPER_ADMIN: ROLE_SUPER_ADMIN,
    "super admin": ROLE_SUPER_ADMIN,
    "super_admin": ROLE_SUPER_ADMIN,
    ROLE_ADMIN: ROLE_COMPANY_ADMIN,
    "admin": ROLE_COMPANY_ADMIN,
    "company admin": ROLE_COMPANY_ADMIN,
    "company_admin": ROLE_COMPANY_ADMIN,
}
F = TypeVar("F", bound=Callable[..., Any])
RESET_OTP_EXPIRES_MINUTES = 10
RESET_OTP_MAX_ATTEMPTS = 5
FORGOT_PASSWORD_RESPONSE = "If account exists, verification code has been sent."


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


def normalize_role(role: Any) -> str:
    raw = _as_str(role).strip()
    return ROLE_ALIASES.get(raw, ROLE_ALIASES.get(raw.lower(), raw))


def _company_id(user: User) -> Optional[int]:
    value = cast(Any, getattr(user, "company_id", None))
    return int(value) if value not in (None, "") else None


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


def _hash_otp(user_id: int, otp: str) -> str:
    payload = f"{user_id}:{otp}".encode("utf-8")
    return hmac.new(Config.JWT_SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(10000):04d}"


def _password_errors(password: str) -> list[str]:
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not any(char.isupper() for char in password):
        errors.append("Password must include an uppercase letter.")
    if not any(char.islower() for char in password):
        errors.append("Password must include a lowercase letter.")
    if not any(char.isdigit() for char in password):
        errors.append("Password must include a number.")
    if not any(not char.isalnum() for char in password):
        errors.append("Password must include a symbol.")
    return errors


def serialize_user(user: User) -> Dict[str, Any]:
    username = _as_str(user.username)
    return {
        "id": _user_id(user),
        "email": _as_str(user.email),
        "username": username,
        "displayName": _as_optional_str(user.display_name) or username,
        "role": normalize_role(user.role),
        "companyId": _company_id(user),
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
        "role": normalize_role(user.role),
        "company_id": _company_id(user),
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


def _latest_reset_otp(session, user_id: int) -> Optional[PasswordResetOtp]:
    return session.execute(
        select(PasswordResetOtp)
        .where(PasswordResetOtp.user_id == user_id)
        .where(PasswordResetOtp.used.is_(False))
        .order_by(desc(PasswordResetOtp.created_at), desc(PasswordResetOtp.id))
        .limit(1)
    ).scalar_one_or_none()


def _reset_otp_invalid(row: PasswordResetOtp, now: datetime) -> bool:
    return (
        bool(row.used)
        or bool(cast(Any, row.expires_at) <= now)
        or int(cast(Any, row.attempt_count) or 0) >= RESET_OTP_MAX_ATTEMPTS
    )


def _find_active_user_by_identifier(session, identifier: str) -> Optional[User]:
    normalized = (identifier or "").strip().lower()
    if not normalized:
        return None
    return session.execute(
        select(User)
        .where(
            or_(
                func.lower(User.email) == normalized,
                func.lower(User.username) == normalized,
            )
        )
        .where(User.is_active.is_(True))
        .limit(1)
    ).scalar_one_or_none()


def request_password_reset_otp(identifier: str) -> Dict[str, Any]:
    normalized_identifier = (identifier or "").strip().lower()
    if not normalized_identifier:
        return {"ok": True, "message": FORGOT_PASSWORD_RESPONSE}

    otp = _generate_otp()
    should_send = False
    recipient_email = ""
    with get_db_session() as session:
        user = _find_active_user_by_identifier(session, normalized_identifier)
        if user:
            now = _now()
            user_id = _user_id(user)
            recipient_email = _as_str(user.email).strip().lower()
            session.execute(
                update(PasswordResetOtp)
                .where(PasswordResetOtp.user_id == user_id)
                .where(PasswordResetOtp.used.is_(False))
                .values(used=True, used_at=now)
            )
            session.add(
                PasswordResetOtp(
                    user_id=user_id,
                    otp_hash=_hash_otp(user_id, otp),
                    expires_at=now + timedelta(minutes=RESET_OTP_EXPIRES_MINUTES),
                    attempt_count=0,
                    verified=False,
                    used=False,
                )
            )
            should_send = True

    if should_send and recipient_email:
        sent = send_password_reset_otp_email(recipient_email, otp)
        if not sent:
            # Public response remains generic to prevent account enumeration.
            detail = get_last_email_error() or "No SMTP detail reported."
            print(f"[AUTH] Password reset OTP email failed for user_id={user_id}: {detail}")
    return {"ok": True, "message": FORGOT_PASSWORD_RESPONSE}


def verify_password_reset_otp(identifier: str, otp: str) -> Tuple[Dict[str, Any], int]:
    normalized_identifier = (identifier or "").strip().lower()
    normalized_otp = (otp or "").strip()
    if not normalized_identifier or not normalized_otp:
        return {"reset_allowed": False, "error": "Account and verification code are required."}, 400
    if not normalized_otp.isdigit() or len(normalized_otp) != 4:
        return {"reset_allowed": False, "error": "Enter the 4 digit verification code."}, 400

    now = _now()
    with get_db_session() as session:
        user = _find_active_user_by_identifier(session, normalized_identifier)
        if not user:
            return {"reset_allowed": False, "error": "Invalid or expired verification code."}, 400

        user_id = _user_id(user)
        otp_row = _latest_reset_otp(session, user_id)
        if not otp_row or _reset_otp_invalid(otp_row, now):
            if otp_row and not bool(otp_row.used):
                otp_row.used = True
                otp_row.used_at = now
            return {"reset_allowed": False, "error": "Invalid or expired verification code."}, 400

        expected_hash = _hash_otp(user_id, normalized_otp)
        if not hmac.compare_digest(str(cast(Any, otp_row.otp_hash)), expected_hash):
            otp_row.attempt_count = int(cast(Any, otp_row.attempt_count) or 0) + 1
            if otp_row.attempt_count >= RESET_OTP_MAX_ATTEMPTS:
                otp_row.used = True
                otp_row.used_at = now
            return {"reset_allowed": False, "error": "Invalid or expired verification code."}, 400

        otp_row.verified = True
        otp_row.verified_at = now
        return {"reset_allowed": True}, 200


def reset_password_with_otp(identifier: str, otp: str, new_password: str) -> Tuple[Dict[str, Any], int]:
    normalized_identifier = (identifier or "").strip().lower()
    normalized_otp = (otp or "").strip()
    if not normalized_identifier or not normalized_otp or not new_password:
        return {"ok": False, "error": "Account, verification code, and new password are required."}, 400
    password_errors = _password_errors(new_password)
    if password_errors:
        return {"ok": False, "error": password_errors[0], "field": "new_password"}, 400

    now = _now()
    with get_db_session() as session:
        user = _find_active_user_by_identifier(session, normalized_identifier)
        if not user:
            return {"ok": False, "error": "Invalid or expired verification code."}, 400

        user_id = _user_id(user)
        otp_row = _latest_reset_otp(session, user_id)
        otp_matches = bool(
            otp_row
            and hmac.compare_digest(str(cast(Any, otp_row.otp_hash)), _hash_otp(user_id, normalized_otp))
        )
        if not otp_row or _reset_otp_invalid(otp_row, now) or not bool(otp_row.verified) or not otp_matches:
            if otp_row and not bool(otp_row.used) and _reset_otp_invalid(otp_row, now):
                otp_row.used = True
                otp_row.used_at = now
            return {"ok": False, "error": "Invalid or expired verification code."}, 400

        user.password_hash = hash_password(new_password)
        otp_row.used = True
        otp_row.used_at = now
        session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    return {"ok": True, "message": "Password updated successfully. Please login again."}, 200


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
            normalized_allowed = {normalize_role(role) for role in required_roles} if required_roles else set()
            if normalized_allowed and normalize_role(user.role) not in normalized_allowed:
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
        def column_exists(table_name: str, column_name: str) -> bool:
            return bool(session.execute(text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                  AND column_name = :column_name
                LIMIT 1
                """
            ), {"table_name": table_name, "column_name": column_name}).scalar_one_or_none())

        session.execute(text(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                website VARCHAR(512),
                industry VARCHAR(120),
                company_size VARCHAR(80),
                country VARCHAR(120),
                plan VARCHAR(80) NOT NULL DEFAULT 'Trial',
                status VARCHAR(30) NOT NULL DEFAULT 'Active',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_companies_name UNIQUE (name),
                CONSTRAINT chk_companies_status CHECK (status IN ('Active', 'Suspended'))
            )
            """
        ))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_status ON companies (status)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies (created_at DESC)"))
        session.execute(text("ALTER TABLE companies ALTER COLUMN plan SET DEFAULT 'Trial'"))
        session.execute(text("ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'Active'"))
        for table_name in [
            "assets",
            "sessions",
            "alerts",
            "active_applications",
            "active_application_history",
            "application_usage_segments",
            "application_usage_daily",
            "activity_sessions",
            "hardware_changes",
        ]:
            if not column_exists(table_name, "company_id"):
                session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL"))
            session.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_company_id ON {table_name} (company_id)"))
        if not column_exists("users", "company_id"):
            session.execute(text("ALTER TABLE users ADD COLUMN company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users (company_id)"))
        if not column_exists("admin_users", "company_id"):
            session.execute(text("ALTER TABLE admin_users ADD COLUMN company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_users_company_id ON admin_users (company_id)"))
        if not column_exists("sessions", "login_source"):
            session.execute(text("ALTER TABLE sessions ADD COLUMN login_source VARCHAR(50)"))
        if not column_exists("sessions", "windows_event_id"):
            session.execute(text("ALTER TABLE sessions ADD COLUMN windows_event_id VARCHAR(20)"))
        if not column_exists("sessions", "windows_event_record_id"):
            session.execute(text("ALTER TABLE sessions ADD COLUMN windows_event_record_id VARCHAR(255)"))
        session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_sessions_windows_event_record_id "
            "ON sessions (windows_event_record_id)"
        ))
        session.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role"))
        session.execute(text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'COMPANY_ADMIN'"))
        session.execute(text(
            """
            UPDATE users
            SET role = CASE lower(role)
                WHEN 'super_admin' THEN 'SUPER_ADMIN'
                WHEN 'super admin' THEN 'SUPER_ADMIN'
                WHEN 'company_admin' THEN 'COMPANY_ADMIN'
                WHEN 'company admin' THEN 'COMPANY_ADMIN'
                WHEN 'admin' THEN 'COMPANY_ADMIN'
                WHEN 'analyst' THEN 'IT Admin'
                WHEN 'it admin' THEN 'IT Admin'
                WHEN 'viewer' THEN 'Viewer'
                ELSE role
            END
            """
        ))
        session.execute(text(
            """
            UPDATE users
            SET role = 'COMPANY_ADMIN'
            WHERE company_id IS NOT NULL
              AND role = 'Viewer'
            """
        ))
        session.execute(text(
            "ALTER TABLE users "
            "ADD CONSTRAINT chk_users_role "
            "CHECK (role IN ('SUPER_ADMIN', 'COMPANY_ADMIN', 'Super Admin', 'Admin', 'IT Admin', 'Viewer'))"
        ))
        session.execute(text(
            """
            INSERT INTO companies (name, website, industry, company_size, country, plan, status)
            SELECT DISTINCT au.company_name, au.company_website, au.industry, au.company_size, au.country, 'Trial', 'Active'
            FROM admin_users au
            WHERE au.company_id IS NULL
            ON CONFLICT (name) DO NOTHING
            """
        ))
        session.execute(text(
            """
            UPDATE admin_users au
            SET company_id = c.id
            FROM companies c
            WHERE au.company_id IS NULL AND c.name = au.company_name
            """
        ))
        session.execute(text(
            """
            UPDATE users u
            SET company_id = au.company_id
            FROM admin_users au
            WHERE u.company_id IS NULL
              AND (lower(u.email) = lower(au.work_email) OR lower(u.username) = lower(au.username))
            """
        ))
        for table_name in [
            "assets",
            "sessions",
            "alerts",
            "active_applications",
            "active_application_history",
            "application_usage_segments",
            "application_usage_daily",
            "activity_sessions",
            "hardware_changes",
        ]:
            session.execute(text(
                f"""
                WITH default_company AS (
                    SELECT id FROM companies
                    WHERE lower(name) = lower(:default_company_name)
                    ORDER BY id DESC
                    LIMIT 1
                )
                UPDATE {table_name}
                SET company_id = (SELECT id FROM default_company)
                WHERE company_id IS NULL
                  AND EXISTS (SELECT 1 FROM default_company)
                """
            ), {"default_company_name": "Asset Sentinel Internal"})
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
        session.execute(text(
            """
            CREATE TABLE IF NOT EXISTS password_reset_otps (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                otp_hash VARCHAR(128) NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                verified BOOLEAN NOT NULL DEFAULT false,
                used BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                verified_at TIMESTAMPTZ,
                used_at TIMESTAMPTZ
            )
            """
        ))
        session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_password_reset_otps_user_created "
            "ON password_reset_otps (user_id, created_at DESC)"
        ))
        session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_password_reset_otps_expires_at "
            "ON password_reset_otps (expires_at)"
        ))
        session.execute(text(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id BIGSERIAL PRIMARY KEY,
                ticket_number VARCHAR(40) NOT NULL,
                company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL,
                created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                title VARCHAR(255) NOT NULL,
                category VARCHAR(120) NOT NULL,
                priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
                description TEXT NOT NULL,
                related_device VARCHAR(255),
                status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
                admin_response TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                resolved_at TIMESTAMPTZ,
                CONSTRAINT uq_support_tickets_ticket_number UNIQUE (ticket_number),
                CONSTRAINT chk_support_tickets_category CHECK (category IN ('Agent Issue', 'Device Offline', 'Login Tracking Issue', 'Application Monitoring Issue', 'Performance Issue', 'Account Issue', 'Other')),
                CONSTRAINT chk_support_tickets_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
                CONSTRAINT chk_support_tickets_status CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'))
            )
            """
        ))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_support_tickets_company_id ON support_tickets (company_id)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets (status)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets (created_at DESC)"))
        session.execute(text("CREATE SEQUENCE IF NOT EXISTS support_ticket_number_seq START 1"))


def bootstrap_admin_user() -> None:
    username = Config.SUPER_ADMIN_USERNAME
    password = Config.SUPER_ADMIN_PASSWORD
    email = Config.SUPER_ADMIN_EMAIL
    if not username or not password or not email:
        print("[AUTH] SUPER_ADMIN bootstrap is not configured; skipping.")
        return
    with get_db_session() as session:
        existing = session.execute(
            select(User)
            .where(User.role.in_([ROLE_SUPER_ADMIN, ROLE_LEGACY_SUPER_ADMIN]))
            .limit(1)
        ).scalar_one_or_none()
        if existing:
            existing.role = ROLE_SUPER_ADMIN
            existing.is_active = True
            existing.company_id = None
            print(f"[AUTH] SUPER_ADMIN ready: username={existing.username}, email={existing.email}")
            return

        session.add(
            User(
                username=username,
                email=email,
                display_name=Config.SUPER_ADMIN_DISPLAY_NAME,
                password_hash=hash_password(password),
                role=ROLE_SUPER_ADMIN,
                company_id=None,
                is_active=True,
                external_provider="local",
                external_subject=username,
            )
        )
        print(f"[AUTH] SUPER_ADMIN created: username={username}, email={email}")
