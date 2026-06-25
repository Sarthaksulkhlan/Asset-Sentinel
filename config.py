import os


class Config:
    SQLALCHEMY_DATABASE_URL = os.environ.get(
        "ASSET_SENTINEL_DATABASE_URL",
        "postgresql+psycopg2://asset_sentinel_app:postgres@localhost:5432/asset_sentinel",
    )
    SQLALCHEMY_ECHO = os.environ.get("ASSET_SENTINEL_SQL_ECHO", "").lower() in {"1", "true", "yes"}
    SQLALCHEMY_POOL_PRE_PING = True
