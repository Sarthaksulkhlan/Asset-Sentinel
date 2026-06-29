import logging
import os
import sys
import threading
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

from monitoring_agent import AssetSentinelAgent
from service_logging import configure_logging


class AssetSentinelMonitoringService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AssetSentinelMonitoringService"
    _svc_display_name_ = "Asset Sentinel Monitoring Service"
    _svc_description_ = (
        "Collects Asset Sentinel endpoint telemetry and uploads hardware, "
        "login, heartbeat, and active application activity to Neon PostgreSQL."
    )

    def __init__(self, args):
        super().__init__(args)
        self.stop_event_handle = win32event.CreateEvent(None, 0, 0, None)
        self.stop_event = threading.Event()
        self.agent = AssetSentinelAgent(stop_event=self.stop_event)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logging.getLogger("asset_sentinel.service").info("Windows Service stop requested.")
        self.stop_event.set()
        win32event.SetEvent(self.stop_event_handle)
        self.agent.stop()

    def SvcDoRun(self):
        os.chdir(Path(__file__).resolve().parent)
        logger = configure_logging("service")
        logger.info("Windows Service starting.")
        servicemanager.LogInfoMsg(f"{self._svc_display_name_} starting")
        try:
            self.agent.start()
            win32event.WaitForSingleObject(self.stop_event_handle, win32event.INFINITE)
        except Exception as exc:
            logger.exception("Windows Service crashed: %s", exc)
            servicemanager.LogErrorMsg(f"{self._svc_display_name_} crashed: {exc}")
            raise
        finally:
            self.stop_event.set()
            self.agent.stop()
            logger.info("Windows Service stopped.")
            servicemanager.LogInfoMsg(f"{self._svc_display_name_} stopped")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AssetSentinelMonitoringService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AssetSentinelMonitoringService)
