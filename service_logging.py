import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
LOG_DIR = ROOT_DIR / "logs"
SERVICE_LOG = LOG_DIR / "service.log"
AGENT_LOG = LOG_DIR / "agent.log"
ERROR_LOG = LOG_DIR / "error.log"


def ensure_log_dir() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def configure_logging(component: str = "agent", console: bool = False) -> logging.Logger:
    ensure_log_dir()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
    )

    component_log = SERVICE_LOG if component == "service" else AGENT_LOG
    component_handler = RotatingFileHandler(
        component_log,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    component_handler.setLevel(logging.INFO)
    component_handler.setFormatter(formatter)
    root.addHandler(component_handler)

    error_handler = RotatingFileHandler(
        ERROR_LOG,
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    logger = logging.getLogger(f"asset_sentinel.{component}")
    logger.info("Logging configured. log_dir=%s", LOG_DIR)
    return logger
