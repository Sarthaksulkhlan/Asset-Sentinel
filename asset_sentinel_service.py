import logging
import os
import subprocess
import sys
import threading
import ctypes
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil
from werkzeug.serving import make_server

from service_logging import configure_logging


SERVICE_NAME = "AssetSentinelMonitoringService"
SERVICE_DISPLAY_NAME = "NEXIS Asset Sentinel Backend Service"
SERVICE_DESCRIPTION = "Runs the Asset Sentinel/NEXIS backend API and supervised endpoint telemetry workers."


class AssetSentinelMonitoringService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args):
        super().__init__(args)
        self.stop_event_handle = win32event.CreateEvent(None, 0, 0, None)
        self.server = None
        self.server_thread = None
        self.flask_app = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logging.getLogger("asset_sentinel.service").info("Windows Service stop requested.")
        if self.server is not None:
            try:
                self.server.shutdown()
            except Exception as exc:
                logging.getLogger("asset_sentinel.service").exception("API server shutdown failed: %s", exc)
        win32event.SetEvent(self.stop_event_handle)

    def SvcDoRun(self):
        root_dir = Path(__file__).resolve().parent
        os.chdir(root_dir)
        logger = configure_logging("service")
        logger.info("Windows Service starting.")
        servicemanager.LogInfoMsg(f"{self._svc_display_name_} starting")
        try:
            self._log_preflight(root_dir)
            from app import app, initialize_backend_runtime

            self.flask_app = app
            initialized = initialize_backend_runtime(start_agent=True, exit_on_error=False)
            if not initialized:
                logger.error("Backend runtime initialization reported failures; API server will still start for diagnostics.")
            self._start_api_server(logger)
            self._log_startup_health(logger)
            win32event.WaitForSingleObject(self.stop_event_handle, win32event.INFINITE)
        except Exception as exc:
            logger.exception("Windows Service crashed: %s", exc)
            servicemanager.LogErrorMsg(f"{self._svc_display_name_} crashed: {exc}")
            raise
        finally:
            if self.server is not None:
                try:
                    self.server.shutdown()
                except Exception:
                    pass
            if self.server_thread is not None:
                self.server_thread.join(timeout=15)
            logger.info("Windows Service stopped.")
            servicemanager.LogInfoMsg(f"{self._svc_display_name_} stopped")

    def _log_preflight(self, root_dir: Path) -> None:
        logger = logging.getLogger("asset_sentinel.service")
        env_path = root_dir / ".env"
        if env_path.exists():
            logger.info("[OK] .env exists: %s", env_path)
        else:
            logger.error("[FAIL] .env exists: missing at %s", env_path)

    def _start_api_server(self, logger: logging.Logger) -> None:
        host = os.environ.get("ASSET_SENTINEL_BACKEND_HOST", "0.0.0.0")
        port = int(os.environ.get("ASSET_SENTINEL_BACKEND_PORT", "5000"))
        if self.flask_app is None:
            raise RuntimeError("Flask app was not loaded before API server startup.")
        self.server = make_server(host, port, self.flask_app, threaded=True)
        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            name="nexis-backend-api-server",
            daemon=True,
        )
        self.server_thread.start()
        logger.info("[OK] API server started: http://%s:%s", host, port)

    def _log_startup_health(self, logger: logging.Logger) -> None:
        from startup_health import startup_health_response

        health = startup_health_response()
        details = health.get("details") or {}
        checks = [
            ("database", "Database connection successful"),
            ("database", "Neon connection successful"),
            ("heartbeat", "Heartbeat thread started"),
            ("login_tracker", "Login tracker started"),
            ("active_application", "Active Application Monitor started"),
            ("telemetry_pipeline", "Scheduler started"),
        ]
        for key, label in checks:
            item = details.get(key) or {}
            ok = health.get(key) == "OK"
            reason = item.get("error") or item.get("last_error") or item.get("reason")
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
