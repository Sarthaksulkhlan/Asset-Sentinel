"""
Asset Sentinel POC — collect_hardware.py
=========================================
Collects hardware information from a Windows machine using WMI.
Part of the Asset Sentinel Proof of Concept (Phase 1 — Hardware Collection).

Run:  python collect_hardware.py
Requires: Python 3.11, pywin32, wmi (Windows only)
"""

import socket
import json
import hashlib
import logging
import ctypes
import os
from ctypes import wintypes
from datetime import datetime, timezone
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Logging — prints to console during POC; swap for file handler in production
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("collect_hardware")


def _configure_foreground_window_api(user32, kernel32) -> None:
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
    user32.SetThreadDesktop.restype = wintypes.BOOL
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL


def _attach_to_input_desktop(user32) -> Optional[int]:
    """
    Attach this thread to the currently active input desktop.

    Windows foreground-window APIs return 0 when a background process has no
    desktop attached. This does not bypass Session 0 isolation; it only lets an
    interactive user-context process read its own real foreground window.
    """
    DESKTOP_READOBJECTS = 0x0001
    DESKTOP_CREATEWINDOW = 0x0002
    DESKTOP_ENUMERATE = 0x0040
    DESKTOP_SWITCHDESKTOP = 0x0100
    access_mask = DESKTOP_READOBJECTS | DESKTOP_CREATEWINDOW | DESKTOP_ENUMERATE | DESKTOP_SWITCHDESKTOP

    desktop = user32.OpenInputDesktop(0, False, access_mask)
    if not desktop:
        logger.debug("OpenInputDesktop returned no desktop handle.")
        return None
    if not user32.SetThreadDesktop(desktop):
        logger.debug("SetThreadDesktop failed for active input desktop.")
        user32.CloseDesktop(desktop)
        return None
    return desktop


def _coinitialize_for_wmi() -> tuple[Any, bool]:
    """
    WMI uses COM. Python threads do not inherit COM initialization, so each
    thread that touches WMI must initialize COM for itself.
    """
    try:
        import pythoncom

        pythoncom.CoInitialize()
        return pythoncom, True
    except ImportError:
        logger.warning("pythoncom is not installed; WMI may fail in threaded collectors.")
    except Exception as exc:
        logger.warning("pythoncom.CoInitialize failed before WMI access: %s", exc)
    return None, False


def _safe_user_object_name(user32, handle: int) -> Optional[str]:
    if not handle:
        return None
    try:
        UOI_NAME = 2
        needed = wintypes.DWORD(0)
        user32.GetUserObjectInformationW.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        user32.GetUserObjectInformationW.restype = wintypes.BOOL
        user32.GetUserObjectInformationW(handle, UOI_NAME, None, 0, ctypes.byref(needed))
        if needed.value <= 0:
            return None
        buffer = ctypes.create_unicode_buffer(max(1, needed.value // ctypes.sizeof(ctypes.c_wchar)))
        if user32.GetUserObjectInformationW(handle, UOI_NAME, buffer, needed, ctypes.byref(needed)):
            return buffer.value or None
    except Exception as exc:
        logger.debug("Could not read Windows user object name: %s", exc)
    return None


def _current_integrity_level() -> Optional[str]:
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        TOKEN_QUERY = 0x0008
        TOKEN_INTEGRITY_LEVEL = 25

        class SID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Sid", wintypes.LPVOID), ("Attributes", wintypes.DWORD)]

        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)):
            return None
        try:
            needed = wintypes.DWORD(0)
            advapi32.GetTokenInformation(token, TOKEN_INTEGRITY_LEVEL, None, 0, ctypes.byref(needed))
            if needed.value <= 0:
                return None
            buffer = ctypes.create_string_buffer(needed.value)
            if not advapi32.GetTokenInformation(
                token,
                TOKEN_INTEGRITY_LEVEL,
                buffer,
                needed,
                ctypes.byref(needed),
            ):
                return None

            sid_and_attributes = ctypes.cast(buffer, ctypes.POINTER(SID_AND_ATTRIBUTES)).contents
            advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
            advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
            count = advapi32.GetSidSubAuthorityCount(sid_and_attributes.Sid).contents.value
            rid = advapi32.GetSidSubAuthority(sid_and_attributes.Sid, count - 1).contents.value
            if rid >= 0x4000:
                return "System"
            if rid >= 0x3000:
                return "High"
            if rid >= 0x2000:
                return "Medium"
            if rid >= 0x1000:
                return "Low"
            return f"Unknown({rid})"
        finally:
            kernel32.CloseHandle(token)
    except Exception as exc:
        logger.debug("Could not determine process integrity level: %s", exc)
        return None


def collect_foreground_diagnostics() -> dict:
    """
    Report the Windows desktop/session context used by foreground collection.
    This makes Session 0 or non-interactive startup failures visible in logs.
    """
    diagnostics: dict[str, Any] = {
        "process_id": os.getpid(),
        "parent_process_id": None,
        "parent_process_name": None,
        "current_session_id": None,
        "active_console_session_id": None,
        "windows_username": os.environ.get("USERDOMAIN", "") + "\\" + os.environ.get("USERNAME", ""),
        "integrity_level": _current_integrity_level(),
        "window_station": None,
        "desktop_name": None,
        "get_foreground_window_null": None,
        "foreground_hwnd": None,
        "get_window_thread_process_id_succeeded": False,
        "foreground_process_id": None,
        "foreground_thread_id": None,
    }

    try:
        import psutil

        process = psutil.Process(os.getpid())
        parent = process.parent()
        diagnostics["parent_process_id"] = process.ppid()
        diagnostics["parent_process_name"] = parent.name() if parent else None
    except Exception as exc:
        diagnostics["parent_process_error"] = str(exc)

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        _configure_foreground_window_api(user32, kernel32)

        active_console_session_id = kernel32.WTSGetActiveConsoleSessionId()
        diagnostics["active_console_session_id"] = int(active_console_session_id)

        session_id = wintypes.DWORD()
        if kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session_id)):
            diagnostics["current_session_id"] = int(session_id.value)

        user32.GetProcessWindowStation.restype = wintypes.HANDLE
        user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
        user32.GetThreadDesktop.restype = wintypes.HANDLE
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        diagnostics["window_station"] = _safe_user_object_name(user32, user32.GetProcessWindowStation())
        diagnostics["desktop_name"] = _safe_user_object_name(
            user32,
            user32.GetThreadDesktop(kernel32.GetCurrentThreadId()),
        )

        hwnd = user32.GetForegroundWindow()
        diagnostics["foreground_hwnd"] = int(hwnd or 0)
        diagnostics["get_foreground_window_null"] = not bool(hwnd)
        if hwnd:
            foreground_pid = wintypes.DWORD()
            thread_id = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(foreground_pid))
            diagnostics["foreground_process_id"] = int(foreground_pid.value)
            diagnostics["foreground_thread_id"] = int(thread_id)
            diagnostics["get_window_thread_process_id_succeeded"] = bool(thread_id and foreground_pid.value)
    except Exception as exc:
        diagnostics["foreground_diagnostic_error"] = str(exc)

    return diagnostics

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Serial number values that OEMs use when they haven't programmed a real value.
# Treat any of these as "not available" (None).
PLACEHOLDER_SERIALS: set[str] = {
    "to be filled by o.e.m.",
    "default string",
    "none",
    "n/a",
    "00000000",
    "0",
    "not applicable",
    "",
    "unknown",
    "system serial number",
    "chassis serial number",
    "base board serial number",
}

# Network adapter description fragments to skip.
# We want physical adapters only — ignore virtual / tunnel / VPN interfaces.
IGNORED_ADAPTER_KEYWORDS: list[str] = [
    "vmware",
    "hyper-v",
    "virtual",
    "vpn",
    "tunnel",
    "bluetooth",
    "miniport",
    "loopback",
    "isatap",
    "teredo",
    "6to4",
    "wan miniport",
    "microsoft wi-fi direct",
    "microsoft hosted network",
    "tap-",          # OpenVPN TAP adapters
    "tap0901",       # OpenVPN legacy
    "cisco",         # Cisco VPN adapters
    "juniper",       # Juniper VPN adapters
]

# All-zeros UUID — means the manufacturer didn't set one
NULL_UUID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Helper: sanitise a serial-number string
# ---------------------------------------------------------------------------

def _sanitise_serial(value: Optional[str]) -> Optional[str]:
    """
    Strip whitespace and return None if the value is a known placeholder.
    Returns the cleaned string otherwise.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned.lower() in PLACEHOLDER_SERIALS:
        logger.debug("Serial value %r recognised as placeholder — treating as None", value)
        return None
    return cleaned


# ---------------------------------------------------------------------------
# Helper: safe WMI query
# ---------------------------------------------------------------------------

def _wmi_query(wmi_conn, wmi_class: str, fields: list[str]) -> list[dict]:
    """
    Execute a WMI query and return a list of dicts.
    Returns an empty list on any error — never raises.
    """
    try:
        results = wmi_conn.query(f"SELECT {', '.join(fields)} FROM {wmi_class}")
        rows = []
        for item in results:
            row = {}
            for field in fields:
                try:
                    row[field] = getattr(item, field, None)
                except Exception:
                    row[field] = None
            rows.append(row)
        return rows
    except Exception as exc:
        logger.warning("WMI query failed for %s: %s", wmi_class, exc)
        return []


# ---------------------------------------------------------------------------
# Individual collectors
# ---------------------------------------------------------------------------

def collect_bios_serial(wmi_conn) -> Optional[str]:
    """Win32_BIOS.SerialNumber — the machine-level serial (Service Tag on Dell)."""
    rows = _wmi_query(wmi_conn, "Win32_BIOS", ["SerialNumber"])
    if rows:
        return _sanitise_serial(rows[0].get("SerialNumber"))
    return None


def collect_baseboard_serial(wmi_conn) -> Optional[str]:
    """Win32_BaseBoard.SerialNumber — the board-level serial."""
    rows = _wmi_query(wmi_conn, "Win32_BaseBoard", ["SerialNumber", "Manufacturer", "Product"])
    if rows:
        return _sanitise_serial(rows[0].get("SerialNumber"))
    return None


def collect_baseboard_details(wmi_conn) -> dict:
    """Return manufacturer and product name from Win32_BaseBoard."""
    rows = _wmi_query(wmi_conn, "Win32_BaseBoard", ["Manufacturer", "Product"])
    if rows:
        return {
            "baseboard_manufacturer": rows[0].get("Manufacturer"),
            "baseboard_product": rows[0].get("Product"),
        }
    return {"baseboard_manufacturer": None, "baseboard_product": None}


def collect_uuid(wmi_conn) -> Optional[str]:
    """Win32_ComputerSystemProduct.UUID — firmware UUID from SMBIOS."""
    rows = _wmi_query(wmi_conn, "Win32_ComputerSystemProduct", ["UUID"])
    if rows:
        value = rows[0].get("UUID")
        if value and value.strip() != NULL_UUID:
            return value.strip()
    return None


def collect_cpu_name(wmi_conn) -> Optional[str]:
    """Win32_Processor.Name — CPU model string."""
    rows = _wmi_query(wmi_conn, "Win32_Processor", ["Name", "ProcessorId"])
    if rows:
        name = rows[0].get("Name")
        return name.strip() if name else None
    return None


def collect_cpu_processor_id(wmi_conn) -> Optional[str]:
    """Win32_Processor.ProcessorId — used as fallback composite component."""
    rows = _wmi_query(wmi_conn, "Win32_Processor", ["ProcessorId"])
    if rows:
        pid = rows[0].get("ProcessorId")
        return pid.strip() if pid else None
    return None


def collect_ram_total_gb(wmi_conn) -> Optional[float]:
    """
    Win32_PhysicalMemory.Capacity — sum across all installed sticks.
    Returns total RAM in GB rounded to 2 decimal places.
    """
    rows = _wmi_query(wmi_conn, "Win32_PhysicalMemory", ["Capacity"])
    if not rows:
        return None
    try:
        total_bytes = sum(
            int(row["Capacity"])
            for row in rows
            if row.get("Capacity") is not None
        )
        if total_bytes == 0:
            return None
        return round(total_bytes / (1024 ** 3), 2)
    except (ValueError, TypeError) as exc:
        logger.warning("Could not calculate total RAM: %s", exc)
        return None


def collect_hostname() -> Optional[str]:
    """socket.gethostname() — always available, no WMI needed."""
    try:
        return socket.gethostname()
    except Exception as exc:
        logger.warning("Could not get hostname: %s", exc)
        return None


def collect_ip_address(hostname: Optional[str]) -> Optional[str]:
    """Resolve the machine's primary IP from its hostname."""
    if not hostname:
        return None
    try:
        ip = socket.gethostbyname(hostname)
        # Ignore loopback — means DNS resolution failed or machine is not networked
        if ip.startswith("127."):
            logger.warning("Hostname resolved to loopback (%s) — no network?", ip)
            return ip
        return ip
    except Exception as exc:
        logger.warning("Could not resolve IP for hostname %r: %s", hostname, exc)
        return None


def collect_mac_address(wmi_conn) -> Optional[str]:
    """
    Find the primary physical network adapter's MAC address.
    Skips virtual, VPN, Bluetooth, and disabled adapters.
    Falls back to uuid.getnode() if WMI returns nothing usable.
    """
    rows = _wmi_query(
        wmi_conn,
        "Win32_NetworkAdapter",
        ["MACAddress", "Description", "AdapterType", "NetEnabled", "NetConnectionStatus"],
    )

    candidates = []
    for row in rows:
        mac = row.get("MACAddress")
        description = (row.get("Description") or "").lower()
        net_enabled = row.get("NetEnabled")
        connection_status = row.get("NetConnectionStatus")

        # Must have a MAC address
        if not mac:
            continue

        # Must be enabled
        if net_enabled is False:
            continue

        # Skip adapters that match ignored keywords
        if any(keyword in description for keyword in IGNORED_ADAPTER_KEYWORDS):
            logger.debug("Skipping adapter %r (matches ignore list)", row.get("Description"))
            continue

        # NetConnectionStatus 2 = connected, 7 = media disconnected (still physical)
        # Prefer connected adapters but don't discard disconnected ones
        priority = 0 if connection_status == 2 else 1
        candidates.append((priority, mac))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    # Fallback: derive MAC from uuid.getnode()
    logger.warning("No physical adapter found via WMI — falling back to uuid.getnode()")
    try:
        import uuid as _uuid
        node = _uuid.getnode()
        mac_hex = f"{node:012X}"
        return ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
    except Exception as exc:
        logger.warning("uuid.getnode() fallback also failed: %s", exc)
        return None


def collect_windows_version() -> Optional[str]:
    """
    Collect Windows version string using the platform module.
    Does not require WMI or admin rights.
    """
    try:
        import platform
        return platform.version()
    except Exception as exc:
        logger.warning("Could not get Windows version: %s", exc)
        return None


def collect_cpu_usage_percent() -> Optional[float]:
    try:
        import psutil
        return round(float(psutil.cpu_percent(interval=0.2)), 2)
    except Exception as exc:
        logger.warning("Could not collect CPU usage with psutil: %s", exc)
    try:
        import wmi
        rows = _wmi_query(wmi.WMI(), "Win32_Processor", ["LoadPercentage"])
        values = [float(row["LoadPercentage"]) for row in rows if row.get("LoadPercentage") is not None]
        if values:
            return round(sum(values) / len(values), 2)
    except Exception as exc:
        logger.warning("Could not collect CPU usage with WMI fallback: %s", exc)
    return None


def collect_ram_usage_percent() -> Optional[float]:
    try:
        import psutil
        return round(float(psutil.virtual_memory().percent), 2)
    except Exception as exc:
        logger.warning("Could not collect RAM usage with psutil: %s", exc)
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(float(status.dwMemoryLoad), 2)
    except Exception as exc:
        logger.warning("Could not collect RAM usage with Windows API fallback: %s", exc)
    return None


def collect_current_active_path() -> dict:
    """
    Collect the current foreground app/window details on Windows.
    Returns browser/document/window context that the dashboard can show as
    the current active path without requiring admin privileges.
    """
    details = {
        "current_website": None,
        "active_window_title": None,
        "active_process_path": None,
        "active_process_name": None,
    }

    try:
        import psutil
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            title = win32gui.GetWindowText(hwnd) or None
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(process_id) if process_id else None
            process_path = process.exe() if process else None
            process_name = process.name() if process else None
            details["active_window_title"] = title
            details["active_process_path"] = process_path
            details["active_process_name"] = process_name
            if title and process_name:
                details["current_website"] = f"{process_name} | {title}"
            elif title:
                details["current_website"] = title
            elif process_name:
                details["current_website"] = process_name
            return details
        logger.debug("win32gui.GetForegroundWindow returned no window handle.")
    except Exception as exc:
        logger.debug("pywin32 foreground collection failed: %s", exc)

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        _configure_foreground_window_api(user32, kernel32)
        input_desktop = _attach_to_input_desktop(user32)

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            logger.debug("GetForegroundWindow returned no window handle.")
            if input_desktop:
                user32.CloseDesktop(input_desktop)
            return details

        title_length = user32.GetWindowTextLengthW(hwnd)
        if title_length > 0:
            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
            details["active_window_title"] = title_buffer.value or None

        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        process_handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            process_id.value,
        )

        if process_handle:
            try:
                path_buffer = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(path_buffer))
                if kernel32.QueryFullProcessImageNameW(
                    process_handle,
                    0,
                    path_buffer,
                    ctypes.byref(size),
                ):
                    process_path = path_buffer.value
                    details["active_process_path"] = process_path
                    details["active_process_name"] = process_path.split("\\")[-1]
            finally:
                kernel32.CloseHandle(process_handle)
        if input_desktop:
            user32.CloseDesktop(input_desktop)

        title = details.get("active_window_title")
        process_name = details.get("active_process_name")
        if title and process_name:
            details["current_website"] = f"{process_name} | {title}"
        elif title:
            details["current_website"] = title
        elif process_name:
            details["current_website"] = process_name

    except Exception as exc:
        logger.warning("Could not collect current active path: %s", exc)

    return details


# ---------------------------------------------------------------------------
# Composite hardware fingerprint (last-resort identifier)
# ---------------------------------------------------------------------------

def build_composite_id(
    baseboard_product: Optional[str],
    cpu_processor_id: Optional[str],
    mac_address: Optional[str],
) -> Optional[str]:
    """
    Build a SHA256 fingerprint from stable, non-serial hardware fields.
    Used only when BIOS serial, BaseBoard serial, and UUID are all unavailable.
    The composite is NOT a serial number — it identifies the hardware combination.
    """
    parts = [
        baseboard_product or "",
        cpu_processor_id or "",
        mac_address or "",
    ]
    if all(p == "" for p in parts):
        logger.error("Composite ID cannot be built — all source fields are empty")
        return None

    fingerprint = "|".join(parts)
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    logger.info("Composite ID built from: %r", fingerprint)
    return digest


# ---------------------------------------------------------------------------
# Determine collection method
# ---------------------------------------------------------------------------

def determine_collection_method(
    bios_serial: Optional[str],
    baseboard_serial: Optional[str],
    uuid: Optional[str],
    composite_id: Optional[str],
) -> str:
    """
    Records which identifier source succeeded, in priority order.
    This field is stored in the DB to track data quality per machine.
    """
    if bios_serial:
        return "bios_serial"
    if baseboard_serial:
        return "baseboard_serial"
    if uuid:
        return "uuid"
    if composite_id:
        return "composite"
    return "none"


# ---------------------------------------------------------------------------
# Main collection function
# ---------------------------------------------------------------------------

def collect_hardware() -> dict:
    """
    Collect all hardware fields from the local Windows machine.
    Returns a single dict — never raises an exception.
    All fields are None if collection fails for that field.
    """
    logger.info("Starting hardware collection...")
    pythoncom_module, com_initialized = _coinitialize_for_wmi()

    result: dict = {
        # Identity fields
        "hostname": None,
        "ip_address": None,
        "mac_address": None,
        # Serial / unique ID fields
        "bios_serial": None,
        "baseboard_serial": None,
        "uuid": None,
        "composite_id": None,
        # Hardware fields
        "cpu_name": None,
        "ram_total_gb": None,
        "cpu_usage_percent": None,
        "ram_usage_percent": None,
        # Motherboard metadata
        "baseboard_manufacturer": None,
        "baseboard_product": None,
        # OS
        "windows_version": None,
        # Current activity
        "current_website": None,
        "active_window_title": None,
        "active_process_path": None,
        "active_process_name": None,
        # Meta
        "collection_method": "none",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "collection_errors": [],
    }

    # -----------------------------------------------------------------------
    # Step 1: Fields that don't need WMI — collect first
    # -----------------------------------------------------------------------
    result["hostname"] = collect_hostname()
    result["ip_address"] = collect_ip_address(result["hostname"])
    result["windows_version"] = collect_windows_version()
    result["cpu_usage_percent"] = collect_cpu_usage_percent()
    result["ram_usage_percent"] = collect_ram_usage_percent()
    result.update(collect_current_active_path())

    # -----------------------------------------------------------------------
    # Step 2: Initialise WMI connection
    # -----------------------------------------------------------------------
    wmi_conn = None
    try:
        import wmi
        wmi_conn = wmi.WMI()
        logger.info("WMI connection established.")
    except ImportError:
        msg = "wmi module not installed. Run: pip install wmi pywin32"
        logger.error(msg)
        result["collection_errors"].append(msg)
    except Exception as exc:
        msg = f"WMI connection failed: {exc}"
        logger.error(msg)
        result["collection_errors"].append(msg)

    # -----------------------------------------------------------------------
    # Step 3: WMI-based collection (skipped gracefully if wmi_conn is None)
    # -----------------------------------------------------------------------
    if wmi_conn is not None:

        # MAC address (WMI-based, with physical adapter filtering)
        try:
            result["mac_address"] = collect_mac_address(wmi_conn)
        except Exception as exc:
            msg = f"MAC address collection failed: {exc}"
            logger.warning(msg)
            result["collection_errors"].append(msg)

        # BIOS serial
        try:
            result["bios_serial"] = collect_bios_serial(wmi_conn)
            if result["bios_serial"]:
                logger.info("BIOS serial collected: %s", result["bios_serial"])
            else:
                logger.warning("BIOS serial is placeholder or unavailable.")
        except Exception as exc:
            msg = f"BIOS serial collection failed: {exc}"
            logger.warning(msg)
            result["collection_errors"].append(msg)

        # BaseBoard serial
        try:
            result["baseboard_serial"] = collect_baseboard_serial(wmi_conn)
            if result["baseboard_serial"]:
                logger.info("BaseBoard serial collected: %s", result["baseboard_serial"])
            else:
                logger.warning("BaseBoard serial is placeholder or unavailable.")
        except Exception as exc:
            msg = f"BaseBoard serial collection failed: {exc}"
            logger.warning(msg)
            result["collection_errors"].append(msg)

        # BaseBoard details (manufacturer + product — used for composite)
        try:
            details = collect_baseboard_details(wmi_conn)
            result["baseboard_manufacturer"] = details["baseboard_manufacturer"]
            result["baseboard_product"] = details["baseboard_product"]
        except Exception as exc:
            msg = f"BaseBoard details collection failed: {exc}"
            logger.warning(msg)
            result["collection_errors"].append(msg)

        # UUID
        try:
            result["uuid"] = collect_uuid(wmi_conn)
            if result["uuid"]:
                logger.info("UUID collected: %s", result["uuid"])
            else:
                logger.warning("UUID is null or unavailable.")
        except Exception as exc:
            msg = f"UUID collection failed: {exc}"
            logger.warning(msg)
            result["collection_errors"].append(msg)

        # CPU name
        try:
            result["cpu_name"] = collect_cpu_name(wmi_conn)
        except Exception as exc:
            msg = f"CPU name collection failed: {exc}"
            logger.warning(msg)
            result["collection_errors"].append(msg)

        # RAM total
        try:
            result["ram_total_gb"] = collect_ram_total_gb(wmi_conn)
        except Exception as exc:
            msg = f"RAM collection failed: {exc}"
            logger.warning(msg)
            result["collection_errors"].append(msg)

    # -----------------------------------------------------------------------
    # Step 4: Composite ID (built if all serial fields are None)
    # -----------------------------------------------------------------------
    if not any([result["bios_serial"], result["baseboard_serial"], result["uuid"]]):
        logger.warning(
            "No serial or UUID found — falling back to composite ID."
        )
        try:
            cpu_processor_id = collect_cpu_processor_id(wmi_conn) if wmi_conn else None
            result["composite_id"] = build_composite_id(
                baseboard_product=result.get("baseboard_product"),
                cpu_processor_id=cpu_processor_id,
                mac_address=result.get("mac_address"),
            )
        except Exception as exc:
            msg = f"Composite ID build failed: {exc}"
            logger.error(msg)
            result["collection_errors"].append(msg)

    # -----------------------------------------------------------------------
    # Step 5: Determine collection method
    # -----------------------------------------------------------------------
    result["collection_method"] = determine_collection_method(
        bios_serial=result["bios_serial"],
        baseboard_serial=result["baseboard_serial"],
        uuid=result["uuid"],
        composite_id=result["composite_id"],
    )

    logger.info(
        "Hardware collection complete. Method: %s | Errors: %d",
        result["collection_method"],
        len(result["collection_errors"]),
    )
    if com_initialized and pythoncom_module is not None:
        try:
            pythoncom_module.CoUninitialize()
        except Exception as exc:
            logger.debug("pythoncom.CoUninitialize failed after WMI access: %s", exc)
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data = collect_hardware()

    print("\n" + "=" * 60)
    print("  ASSET SENTINEL — Hardware Collection Result")
    print("=" * 60)
    print(json.dumps(data, indent=2, default=str))
    print("=" * 60)

    # Summary
    print("\nSUMMARY")
    print(f"  Hostname        : {data['hostname']}")
    print(f"  IP Address      : {data['ip_address']}")
    print(f"  MAC Address     : {data['mac_address']}")
    print(f"  BIOS Serial     : {data['bios_serial'] or '[placeholder/unavailable]'}")
    print(f"  BaseBoard Serial: {data['baseboard_serial'] or '[placeholder/unavailable]'}")
    print(f"  UUID            : {data['uuid'] or '[null/unavailable]'}")
    print(f"  Composite ID    : {data['composite_id'] or '[not needed]'}")
    print(f"  CPU             : {data['cpu_name']}")
    print(f"  CPU Usage       : {data.get('cpu_usage_percent')}%")
    print(f"  RAM             : {data['ram_total_gb']} GB")
    print(f"  RAM Usage       : {data.get('ram_usage_percent')}%")
    print(f"  Windows Version : {data['windows_version']}")
    print(f"  Active Path     : {data.get('current_website') or '[unavailable]'}")
    print(f"  Collection Method: {data['collection_method'].upper()}")

    if data["collection_errors"]:
        print(f"\n  WARNINGS ({len(data['collection_errors'])}):")
        for err in data["collection_errors"]:
            print(f"    - {err}")
    else:
        print("\n  No errors during collection.")
