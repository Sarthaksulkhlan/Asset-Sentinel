from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
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


def _database_connection_error_message() -> str:
    return (
        "\n[DATABASE] Could not connect to PostgreSQL.\n"
        f"[DATABASE] SQLAlchemy URL: {_database_url_for_display()}\n\n"
        "Asset Sentinel is configured to use PostgreSQL at startup, but the "
        "database server is not accepting connections. Start PostgreSQL and "
        "create the configured database, or point ASSET_SENTINEL_DATABASE_URL "
        "at a running PostgreSQL instance.\n\n"
        "Expected local defaults:\n"
        "  host: localhost\n"
        "  port: 5432\n"
        "  database: asset_sentinel\n"
        "  user: postgres\n\n"
        "Example PowerShell override:\n"
        "  $env:ASSET_SENTINEL_DATABASE_URL="
        "'postgresql+psycopg2://postgres:postgres@localhost:5432/asset_sentinel'\n"
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

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        raise RuntimeError(_database_connection_error_message()) from exc

