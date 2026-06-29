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

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        raise RuntimeError(_database_connection_error_message()) from exc

