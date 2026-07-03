from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import Config


engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URL,
    echo=Config.SQLALCHEMY_ECHO,
    pool_pre_ping=Config.SQLALCHEMY_POOL_PRE_PING,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def _database_url_for_display() -> str:
    try:
        return make_url(Config.SQLALCHEMY_DATABASE_URL).render_as_string(hide_password=True)
    except Exception:
        return Config.SQLALCHEMY_DATABASE_URL


def database_host_for_display() -> str:
    try:
        return make_url(Config.SQLALCHEMY_DATABASE_URL).host or "unknown"
    except Exception:
        return "unknown"


def assert_neon_postgresql_url() -> None:
    url = make_url(Config.SQLALCHEMY_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        raise RuntimeError("SQLite is not supported. Set ASSET_SENTINEL_DATABASE_URL to the Neon PostgreSQL URL.")
    if "postgresql" not in url.drivername:
        raise RuntimeError("Asset Sentinel requires PostgreSQL via ASSET_SENTINEL_DATABASE_URL.")
    host = (url.host or "").lower()
    if "localhost" in host or host.startswith("127.") or host == "::1":
        raise RuntimeError("Local PostgreSQL is not allowed. Use the Neon host in ASSET_SENTINEL_DATABASE_URL.")


def _database_connection_error_message() -> str:
    return (
        "\n[DATABASE] Could not connect to PostgreSQL.\n"
        f"[DATABASE] SQLAlchemy URL: {_database_url_for_display()}\n\n"
        "Asset Sentinel now requires ASSET_SENTINEL_DATABASE_URL for every "
        "SQLAlchemy connection. Confirm the Neon PostgreSQL URL is present, "
        "reachable, and includes the required SSL options.\n"
    )


@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    import models  # noqa: F401

    assert_neon_postgresql_url()
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        raise RuntimeError(_database_connection_error_message()) from exc


REQUIRED_TABLES = {
    "assets",
    "sessions",
    "alerts",
    "active_applications",
    "active_application_history",
    "hardware_changes",
    "users",
    "refresh_tokens",
    "admin_users",
    "early_access_requests",
}


def verify_database_health() -> dict:
    report = {
        "connected": False,
        "schema_ok": False,
        "required_tables_ok": False,
        "missing_tables": [],
        "error": None,
    }
    try:
        assert_neon_postgresql_url()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        report["connected"] = True
        init_db()
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        missing = sorted(REQUIRED_TABLES - existing_tables)
        report["missing_tables"] = missing
        report["required_tables_ok"] = not missing
        report["schema_ok"] = not missing
    except Exception as exc:
        report["error"] = str(exc)
    return report

