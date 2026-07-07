import os
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_ENV_LOADED = False
ROOT_DIR = Path(__file__).resolve().parents[2]
_ENV_PATH = str(ROOT_DIR / ".env")


def _load_local_env_file(force: bool = False) -> None:
    """Load simple KEY=VALUE pairs from .env without overriding real env vars."""
    global _ENV_LOADED
    if _ENV_LOADED and not force:
        return
    _ENV_LOADED = True

    if not os.path.exists(_ENV_PATH):
        return

    with open(_ENV_PATH, "r", encoding="utf-8-sig") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and (force or not os.environ.get(key)):
                os.environ[key] = value


_load_local_env_file()


def _display_tzinfo():
    name = os.environ.get("ASSET_SENTINEL_DISPLAY_TIMEZONE", "Asia/Kolkata")
    try:
        return name, ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name in {"Asia/Kolkata", "Asia/Calcutta"}:
            return name, timezone(timedelta(hours=5, minutes=30))
        raise


def _required_database_url() -> str:
    value = os.environ.get("ASSET_SENTINEL_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "ASSET_SENTINEL_DATABASE_URL is required. Configure it with the Neon "
            "PostgreSQL connection string before starting Asset Sentinel."
        )
    return value


class Config:
    SQLALCHEMY_DATABASE_URL = _required_database_url()
    SQLALCHEMY_ECHO = os.environ.get("ASSET_SENTINEL_SQL_ECHO", "").lower() in {"1", "true", "yes"}
    SQLALCHEMY_POOL_PRE_PING = True
    HEARTBEAT_TIMEOUT_SECONDS = int(os.environ.get("ASSET_SENTINEL_HEARTBEAT_TIMEOUT_SECONDS", "45"))
    HEARTBEAT_FUTURE_SKEW_SECONDS = int(os.environ.get("ASSET_SENTINEL_HEARTBEAT_FUTURE_SKEW_SECONDS", "10"))
    DISPLAY_TIMEZONE, DISPLAY_TZINFO = _display_tzinfo()
    JWT_SECRET_KEY = os.environ.get("ASSET_SENTINEL_JWT_SECRET", "your_secret_here")
    JWT_ISSUER = os.environ.get("ASSET_SENTINEL_JWT_ISSUER", "asset-sentinel")
    JWT_AUDIENCE = os.environ.get("ASSET_SENTINEL_JWT_AUDIENCE", "asset-sentinel-frontend")
    JWT_ACCESS_TOKEN_MINUTES = int(os.environ.get("ASSET_SENTINEL_ACCESS_TOKEN_MINUTES", "15"))
    JWT_REFRESH_TOKEN_DAYS = int(os.environ.get("ASSET_SENTINEL_REFRESH_TOKEN_DAYS", "7"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=JWT_ACCESS_TOKEN_MINUTES)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=JWT_REFRESH_TOKEN_DAYS)
    BOOTSTRAP_ADMIN_USERNAME = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_USERNAME", "centralcommand")
    BOOTSTRAP_ADMIN_EMAIL = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_EMAIL", "centralcommand@asset-sentinel.local")
    BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_PASSWORD", "your_admin_password")
    BOOTSTRAP_ADMIN_DISPLAY_NAME = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_DISPLAY_NAME", "Central Command")
    SUPER_ADMIN_USERNAME = os.environ.get("SUPER_ADMIN_USERNAME", BOOTSTRAP_ADMIN_USERNAME)
    SUPER_ADMIN_EMAIL = os.environ.get("SUPER_ADMIN_EMAIL", BOOTSTRAP_ADMIN_EMAIL)
    SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", BOOTSTRAP_ADMIN_PASSWORD)
    SUPER_ADMIN_DISPLAY_NAME = os.environ.get("SUPER_ADMIN_DISPLAY_NAME", BOOTSTRAP_ADMIN_DISPLAY_NAME)
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", SMTP_USERNAME)
    SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "").lower() in {"1", "true", "yes"}
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
    ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
    SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", ALERT_EMAIL)

    @classmethod
    def refresh_from_environment(cls) -> None:
        cls.SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        cls.SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
        cls.SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
        cls.SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
        cls.SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", cls.SMTP_USERNAME)
        cls.SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "").lower() in {"1", "true", "yes"}
        cls.SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
        cls.ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
        cls.SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", cls.ALERT_EMAIL)
        cls.SUPER_ADMIN_USERNAME = os.environ.get("SUPER_ADMIN_USERNAME", cls.BOOTSTRAP_ADMIN_USERNAME)
        cls.SUPER_ADMIN_EMAIL = os.environ.get("SUPER_ADMIN_EMAIL", cls.BOOTSTRAP_ADMIN_EMAIL)
        cls.SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", cls.BOOTSTRAP_ADMIN_PASSWORD)
        cls.SUPER_ADMIN_DISPLAY_NAME = os.environ.get("SUPER_ADMIN_DISPLAY_NAME", cls.BOOTSTRAP_ADMIN_DISPLAY_NAME)

    @classmethod
    def reload_local_env(cls) -> None:
        _load_local_env_file(force=True)
        cls.refresh_from_environment()


def print_startup_environment_diagnostics() -> None:
    _load_local_env_file(force=True)
    Config.refresh_from_environment()
    print(f"Loaded .env: {_ENV_PATH}")
    print(f"Exists: {os.path.exists(_ENV_PATH)}")
    print(f"Config module: {os.path.abspath(__file__)}")
    print(f"Working directory: {os.getcwd()}")
    print(f"SMTP_HOST: {'FOUND' if Config.SMTP_HOST else 'MISSING'}")
    print(f"SMTP_USERNAME: {'FOUND' if Config.SMTP_USERNAME else 'MISSING'}")
    print(f"SMTP_PASSWORD: {'FOUND' if Config.SMTP_PASSWORD else 'MISSING'}")
