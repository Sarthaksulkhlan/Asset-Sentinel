import logging
import os
import subprocess
import sys
import threading
import ctypes
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
for path in [
    ROOT_DIR,
    ROOT_DIR / "backend" / "api",
    ROOT_DIR / "backend" / "core",
    ROOT_DIR / "backend" / "models",
    ROOT_DIR / "backend" / "services",
    ROOT_DIR / "agent" / "collectors",
    ROOT_DIR / "agent" / "detectors",
    ROOT_DIR / "agent" / "windows",
    ROOT_DIR / "agent" / "client",
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

import servicemanager
import win32event
import win32service
import win32serviceutil

from service_logging import configure_logging


SERVICE_NAME = "AssetSentinelMonitoringService"
SERVICE_DISPLAY_NAME = "NEXIS Asset Sentinel Windows Agent"
SERVICE_DESCRIPTION = "Runs the Asset Sentinel Windows telemetry agent and sends endpoint telemetry to the Render backend."
RENDER_API_URL = "https://asset-sentinel-backend.onrender.com"
DEFAULT_DEVELOPMENT_AGENT_TOKEN = "asset-sentinel-development-agent-token"


def load_service_env(force: bool = True) -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8-sig") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and (force or not os.environ.get(key)):
                os.environ[key] = value


def validate_agent_environment() -> None:
    load_service_env(force=True)
    api_url = (os.environ.get("ASSET_SENTINEL_API_URL") or "").strip().rstrip("/")
    token = (os.environ.get("ASSET_SENTINEL_AGENT_TOKEN") or "").strip()
    if api_url != RENDER_API_URL:
        raise RuntimeError(
            f"ASSET_SENTINEL_API_URL must be {RENDER_API_URL}. "
            "The Windows Service must not target localhost or a local backend."
        )
    if not token or token == DEFAULT_DEVELOPMENT_AGENT_TOKEN:
        raise RuntimeError("ASSET_SENTINEL_AGENT_TOKEN must be configured with the Render agent token.")


class AssetSentinelMonitoringService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args):
        super().__init__(args)
        self.stop_event_handle = win32event.CreateEvent(None, 0, 0, None)
        self.agent_stop_event = threading.Event()
        self.agent = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logging.getLogger("asset_sentinel.service").info("Windows Service stop requested.")
        self.agent_stop_event.set()
        if self.agent is not None:
            try:
                self.agent.stop()
            except Exception as exc:
                logging.getLogger("asset_sentinel.service").exception("Agent shutdown failed: %s", exc)
        win32event.SetEvent(self.stop_event_handle)

    def SvcDoRun(self):
        root_dir = ROOT_DIR
        os.chdir(root_dir)
        logger = configure_logging("service")
        logger.info("Windows Service starting.")
        servicemanager.LogInfoMsg(f"{self._svc_display_name_} starting")
        try:
            self._log_preflight(root_dir)
            validate_agent_environment()
            from monitoring_agent import AssetSentinelAgent
            from api_client import client

            logger.info("[OK] Agent API URL: %s", client().base_url)
            logger.info("[OK] Backend mode: Render API only; local PostgreSQL/backend startup skipped.")
            self.agent = AssetSentinelAgent(stop_event=self.agent_stop_event)
            self.agent.start()
            self._log_agent_health(logger)
            win32event.WaitForSingleObject(self.stop_event_handle, win32event.INFINITE)
        except Exception as exc:
            logger.exception("Windows Service crashed: %s", exc)
            servicemanager.LogErrorMsg(f"{self._svc_display_name_} crashed: {exc}")
            raise
        finally:
            self.agent_stop_event.set()
            if self.agent is not None:
                try:
                    self.agent.stop()
                except Exception:
                    pass
            logger.info("Windows Service stopped.")
            servicemanager.LogInfoMsg(f"{self._svc_display_name_} stopped")

    def _log_preflight(self, root_dir: Path) -> None:
        logger = logging.getLogger("asset_sentinel.service")
        env_path = root_dir / ".env"
        if env_path.exists():
            logger.info("[OK] .env exists: %s", env_path)
        else:
            logger.error("[FAIL] .env exists: missing at %s", env_path)

    def _log_agent_health(self, logger: logging.Logger) -> None:
        snapshot = self.agent.health_snapshot() if self.agent is not None else {}
        threads = snapshot.get("threads") or {}
        checks = [
            ("heartbeat", "Heartbeat thread started"),
            ("login-activity", "Login tracker started"),
            ("active-application", "Active Application Monitor started"),
            ("spool-retry", "Telemetry spool retry started"),
            ("hardware-inventory", "Hardware inventory scheduler started"),
            ("thread-watchdog", "Thread watchdog started"),
        ]
        for key, label in checks:
            item = threads.get(key) or {}
            ok = bool(item.get("alive"))
            reason = None
            if ok:
                logger.info("[OK] %s", label)
            else:
                logger.error("[FAIL] %s%s", label, f": {reason}" if reason else "")


def _run_sc_command(args: list[str]) -> None:
    completed = subprocess.run(
        ["sc.exe", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"sc.exe {' '.join(args)} failed: {detail}")


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _install_frozen_service() -> None:
    root_dir = Path(sys.executable).resolve().parent
    os.chdir(root_dir)
    logger = configure_logging("service")
    if not _is_admin():
        logger.error("NEXIS Agent.exe must be run as Administrator to install the Windows Service.")
        raise SystemExit(1)
    if not (root_dir / ".env").exists():
        logger.error(".env file is missing at %s. Configure .env before installing the service.", root_dir / ".env")
        raise SystemExit(1)
    validate_agent_environment()

    exe_path = str(Path(sys.executable).resolve())
    logger.info("Installing frozen NEXIS service from %s", exe_path)
    subprocess.run(["sc.exe", "stop", SERVICE_NAME], capture_output=True, text=True, check=False)
    subprocess.run(["sc.exe", "delete", SERVICE_NAME], capture_output=True, text=True, check=False)
    _run_sc_command([
        "create",
        SERVICE_NAME,
        "binPath=",
        f'"{exe_path}"',
        "DisplayName=",
        SERVICE_DISPLAY_NAME,
        "start=",
        "delayed-auto",
    ])
    _run_sc_command(["description", SERVICE_NAME, SERVICE_DESCRIPTION])
    _run_sc_command([
        "failure",
        SERVICE_NAME,
        "reset=",
        "86400",
        "actions=",
        "restart/60000/restart/120000/restart/300000",
    ])
    _run_sc_command(["failureflag", SERVICE_NAME, "1"])
    _run_sc_command(["start", SERVICE_NAME])
    logger.info("NEXIS Windows Service installed and started.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AssetSentinelMonitoringService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception:
            if getattr(sys, "frozen", False):
                _install_frozen_service()
            else:
                raise
    else:
        win32serviceutil.HandleCommandLine(AssetSentinelMonitoringService)
