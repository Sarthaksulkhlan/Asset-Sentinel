import os
from datetime import timedelta


class Config:
    POSTGRES_USER = os.environ.get("ASSET_SENTINEL_DB_USER", "postgres")
    POSTGRES_PASSWORD = os.environ.get("ASSET_SENTINEL_DB_PASSWORD", "postgres")
    POSTGRES_HOST = os.environ.get("ASSET_SENTINEL_DB_HOST", "localhost")
    POSTGRES_PORT = os.environ.get("ASSET_SENTINEL_DB_PORT", "5432")
    POSTGRES_DB = os.environ.get("ASSET_SENTINEL_DB_NAME", "asset_sentinel")
    SQLALCHEMY_DATABASE_URL = os.environ.get(
        "ASSET_SENTINEL_DATABASE_URL",
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
    )
    SQLALCHEMY_ECHO = os.environ.get("ASSET_SENTINEL_SQL_ECHO", "").lower() in {"1", "true", "yes"}
    SQLALCHEMY_POOL_PRE_PING = True
    JWT_SECRET_KEY = os.environ.get("ASSET_SENTINEL_JWT_SECRET", "change-me-before-production")
    JWT_ISSUER = os.environ.get("ASSET_SENTINEL_JWT_ISSUER", "asset-sentinel")
    JWT_AUDIENCE = os.environ.get("ASSET_SENTINEL_JWT_AUDIENCE", "asset-sentinel-frontend")
    JWT_ACCESS_TOKEN_MINUTES = int(os.environ.get("ASSET_SENTINEL_ACCESS_TOKEN_MINUTES", "15"))
    JWT_REFRESH_TOKEN_DAYS = int(os.environ.get("ASSET_SENTINEL_REFRESH_TOKEN_DAYS", "7"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=JWT_ACCESS_TOKEN_MINUTES)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=JWT_REFRESH_TOKEN_DAYS)
    BOOTSTRAP_ADMIN_USERNAME = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_USERNAME", "sentinelcommand")
    BOOTSTRAP_ADMIN_EMAIL = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_EMAIL", "sentinelcommand@asset-sentinel.local")
    BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_PASSWORD", "assetsentinel.alert")
    BOOTSTRAP_ADMIN_DISPLAY_NAME = os.environ.get("ASSET_SENTINEL_BOOTSTRAP_ADMIN_DISPLAY_NAME", "Sentinel Command")
