from contextlib import contextmanager

from sqlalchemy import create_engine
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

    Base.metadata.create_all(bind=engine)

