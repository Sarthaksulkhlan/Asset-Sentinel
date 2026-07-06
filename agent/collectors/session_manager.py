from pathlib import Path
import sys

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
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
"""
Asset Sentinel Session Manager
================================
Provides Windows session information using WMI and system APIs.

This module retrieves current login session details:
- Current username (with domain prefix)
- Hostname
- Current IP address
- Windows Session ID
- Login timestamp
- Device online status

Use this as the foundation for login tracking and session monitoring.
Can be extended for Windows Service deployment.

Requires: pywin32, psutil (Windows only)
"""

import socket
import logging
import ctypes
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import os

try:
    import wmi
except ImportError:
    wmi = None

try:
    import pythoncom
except ImportError:
    pythoncom = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32evtlog
except ImportError:
    win32evtlog = None

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger("session_manager")


def _coinitialize_for_wmi() -> bool:
    if pythoncom is None:
        logger.warning("pythoncom not available; WMI session lookup may fail in threads")
        return False
    try:
        pythoncom.CoInitialize()
        return True
    except Exception as exc:
        logger.warning("pythoncom.CoInitialize failed before WMI session lookup: %s", exc)
        return False


# ============================================================================
# Core Session Information Functions
# ============================================================================

def get_current_username() -> Optional[str]:
    """
    Get the currently logged-in Windows username.
    
    Returns the username from the USERNAME environment variable.
    On domain-joined machines, typically returns 'DOMAIN\\username'.
    
    Returns:
        str: Current username, e.g. 'DESKTOP-PETBKU1\\Sarthak'
        None: If unable to determine username
    """
    try:
        # Windows API approach - gets domain\username format if on domain
        username = os.environ.get("USERNAME")
        if username:
            return username.strip()
        logger.warning("USERNAME environment variable not set")
        return None
    except Exception as e:
        logger.error(f"Error getting username: {e}")
        return None


def get_current_hostname() -> Optional[str]:
    """
    Get the Windows hostname.
    
    Returns:
        str: Machine hostname, e.g. 'DESKTOP-PETBKU1'
        None: If unable to determine hostname
    """
    try:
        hostname = socket.gethostname()
        if hostname:
            return hostname.strip()
        logger.warning("Could not determine hostname")
        return None
    except Exception as e:
        logger.error(f"Error getting hostname: {e}")
        return None


def get_current_ip_address() -> Optional[str]:
    """
    Get the primary IPv4 address of the local machine.
    
    Uses socket to determine the primary network interface IP.
    Connects to Google's DNS (8.8.8.8) to determine the route,
    then returns the local IP without actually sending data.
    
    Returns:
        str: IPv4 address, e.g. '192.168.1.5'
        None: If unable to determine IP
    """
    try:
        # Method: determine routing to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        if ip_address:
            return ip_address.strip()
        logger.warning("Could not determine IP address")
        return None
    except Exception as e:
        logger.warning(f"Error getting IP address (will retry with localhost): {e}")
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception as e2:
            logger.error(f"Fallback IP resolution failed: {e2}")
            return None


def get_session_id_via_wmi() -> Optional[str]:
    """
    Get the Windows Session ID using WMI.
    
    Queries Win32_LogonSession to find active login sessions.
    Returns the SessionID of the current user's session.
    
    Returns:
        str: Session ID (e.g., '1' for user session, '0' for system)
        None: If unable to determine Session ID
    """
    if wmi is None:
        logger.warning("pywin32/wmi not available, cannot get Session ID via WMI")
        return get_session_id_via_windows_api()

    com_initialized = _coinitialize_for_wmi()
    try:
        current_username = get_current_username()
        if not current_username:
            logger.warning("Cannot determine Session ID - username unknown")
            return None
        
        wmi_conn = wmi.WMI()
        
        # Query Win32_LogonSession for active sessions
        sessions = wmi_conn.query("SELECT SessionID FROM Win32_LogonSession WHERE LogonType != 0")
        
        if sessions:
            # Return the first active session ID
            session_id = sessions[0].SessionID
            if session_id is not None:
                return str(session_id)
        
        logger.warning("No active sessions found via WMI")
        return None
        
    except Exception as e:
        logger.warning(f"Error querying Session ID via WMI: {e}")
        return get_session_id_via_windows_api()
    finally:
        if com_initialized and pythoncom is not None:
            try:
                pythoncom.CoUninitialize()
            except Exception as exc:
                logger.debug("pythoncom.CoUninitialize failed after WMI session lookup: %s", exc)


def get_session_id_via_windows_api() -> Optional[str]:
    try:
        session_id = ctypes.c_ulong()
        process_id = os.getpid()
        if ctypes.windll.kernel32.ProcessIdToSessionId(process_id, ctypes.byref(session_id)):
            return str(session_id.value)
        logger.warning("ProcessIdToSessionId returned false for current process")
    except Exception as exc:
        logger.warning(f"Windows API session ID fallback failed: {exc}")
    return None


def get_login_timestamp() -> str:
    """
    Get the current UTC timestamp in ISO 8601 format.
    
    This represents when this session check occurred.
    For accurate login time, integrate with Windows Event Log in future.
    
    Returns:
        str: ISO 8601 timestamp with timezone, e.g. '2026-06-17T10:30:45.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


def _normalize_windows_username(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.split("\\")[-1].split("@")[0].strip().lower()


def _event_time_to_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.astimezone(timezone.utc)
        local_tz = datetime.now().astimezone().tzinfo
        return value.replace(tzinfo=local_tz).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _parse_iso_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc)
    return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo).astimezone(timezone.utc)


def _read_latest_windows_security_event(
    username: Optional[str],
    event_ids: set[int],
    interactive_logons_only: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Read the Windows Security log and return the newest matching event for
    the active user. EventID is masked because pywin32 may include qualifiers.
    """
    if win32evtlog is None or os.name != "nt":
        return None

    normalized_user = _normalize_windows_username(username)
    if not normalized_user:
        return None

    server = None
    log_name = "Security"
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    try:
        handle = win32evtlog.OpenEventLog(server, log_name)
    except Exception as exc:
        logger.warning(
            "Could not open Windows Security event log for event_ids=%s: %s. "
            "Login tracker will use non-admin observed-session fallback if available.",
            sorted(event_ids),
            exc,
        )
        return None

    try:
        scanned = 0
        while scanned < 2500:
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            if not events:
                break
            for event in events:
                scanned += 1
                event_id = int(event.EventID) & 0xFFFF
                if event_id not in event_ids:
                    continue

                generated_at = _event_time_to_utc(event.TimeGenerated)
                if generated_at < cutoff:
                    logger.info(
                        "Windows login event rejected: event_id=%s record_id=%s reason=older_than_cutoff timestamp=%s",
                        event_id,
                        event.RecordNumber,
                        generated_at.isoformat(),
                    )
                    return None

                inserts = [str(value) for value in (event.StringInserts or [])]
                lowered = [_normalize_windows_username(value) for value in inserts]
                logger.info(
                    "Windows login event received: event_id=%s record_id=%s timestamp=%s user_match=%s inserts=%s",
                    event_id,
                    event.RecordNumber,
                    generated_at.isoformat(),
                    normalized_user in lowered,
                    inserts,
                )
                if normalized_user not in lowered:
                    logger.info(
                        "Windows login event rejected: event_id=%s record_id=%s reason=username_not_matched expected=%s",
                        event_id,
                        event.RecordNumber,
                        normalized_user,
                    )
                    continue

                login_source = "windows_unlock" if event_id == 4801 else "windows_interactive_logon"
                logon_type = None
                if event_id == 4624 and len(inserts) > 8:
                    logon_type = inserts[8]
                    if interactive_logons_only and logon_type != "2":
                        logger.info(
                            "Windows login event rejected: event_id=%s record_id=%s reason=non_interactive_logon_type logon_type=%s",
                            event_id,
                            event.RecordNumber,
                            logon_type,
                        )
                        continue
                elif event_id == 4778:
                    login_source = "windows_unlock"
                elif event_id == 4634:
                    login_source = "windows_logoff"
                elif event_id == 4647:
                    login_source = "windows_user_logoff"
                elif event_id == 4779:
                    login_source = "windows_session_disconnect"
                elif event_id == 4800:
                    login_source = "windows_lock"

                logger.info(
                    "Windows login event accepted: event_id=%s record_id=%s source=%s logon_type=%s",
                    event_id,
                    event.RecordNumber,
                    login_source,
                    logon_type,
                )
                return {
                    "event_id": str(event_id),
                    "event_record_id": str(event.RecordNumber),
                    "event_timestamp": generated_at.isoformat(),
                    "login_source": login_source,
                    "logon_type": logon_type,
                }
    except Exception as exc:
        logger.warning(f"Could not read Windows login events: {exc}")
    finally:
        try:
            win32evtlog.CloseEventLog(handle)
        except Exception:
            pass

    return None


def get_latest_windows_login_event(username: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Return the newest interactive Windows login boundary for this user.

    Security 4624 logon type 2 is a full interactive login. Unlocks are
    session-state events, not new work sessions.
    """
    return _read_latest_windows_security_event(username, {4624}, True)


def get_latest_windows_unlock_event(username: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return the newest Windows unlock or reconnect event for this user."""
    return _read_latest_windows_security_event(username, {4801, 4778}, False)


def get_latest_windows_logout_event(username: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return the newest Windows lock, disconnect, or logoff event for this user."""
    return _read_latest_windows_security_event(username, {4634, 4647, 4779, 4800}, False)


def get_device_status() -> str:
    """
    Get the current device status from heartbeat state only.
    
    Returns:
        str: 'Online' if latest heartbeat is fresh, 'Offline' otherwise
    """
    try:
        from storage import get_asset_status

        status = get_asset_status(get_current_hostname() or socket.gethostname()) or {}
        return status.get("device_status") or "Offline"
    except Exception as exc:
        logger.warning("Could not resolve heartbeat-backed device status: %s", exc)
        return "Offline"


# ============================================================================
# Consolidated Session Info
# ============================================================================

def get_current_session_info() -> Dict[str, Any]:
    """
    Get comprehensive current Windows session information.
    
    This is the primary function to call for login tracking.
    Collects all session details in one call.
    
    Returns:
        dict: Session information containing:
            - username: str - Current logged-in username
            - hostname: str - Machine hostname
            - ip_address: str - Primary IPv4 address
            - session_id: str - Windows Session ID
            - login_timestamp: str - ISO 8601 timestamp
            - device_status: str - 'Online' or 'Offline'
            - collection_timestamp: str - When this data was collected
            
    Example:
        {
            "username": "DESKTOP-PETBKU1\\Sarthak",
            "hostname": "DESKTOP-PETBKU1",
            "ip_address": "192.168.1.5",
            "session_id": "1",
            "login_timestamp": "2026-06-17T10:30:45.123456+00:00",
            "device_status": "Online",
            "collection_timestamp": "2026-06-17T10:30:45.123456+00:00"
        }
    """
    username = get_current_username()
    login_event = get_latest_windows_login_event(username)
    unlock_event = get_latest_windows_unlock_event(username)
    logout_event = get_latest_windows_logout_event(username)
    login_boundary = login_event
    login_boundary_time = _parse_iso_utc(login_event.get("event_timestamp")) if login_event else None
    unlock_boundary_time = _parse_iso_utc(unlock_event.get("event_timestamp")) if unlock_event else None
    logout_boundary_time = _parse_iso_utc(logout_event.get("event_timestamp")) if logout_event else None
    if unlock_event and (
        login_boundary_time is None
        or (unlock_boundary_time and unlock_boundary_time > login_boundary_time)
    ):
        login_boundary = unlock_event
        login_boundary_time = unlock_boundary_time
    login_timestamp = login_boundary.get("event_timestamp") if login_boundary else get_login_timestamp()
    if logout_boundary_time and login_boundary_time and logout_boundary_time > login_boundary_time:
        login_timestamp = get_login_timestamp()
    session_info = {
        "username": username,
        "hostname": get_current_hostname(),
        "ip_address": get_current_ip_address(),
        "session_id": get_session_id_via_wmi(),
        "login_timestamp": login_timestamp,
        "login_source": login_boundary.get("login_source") if login_boundary else "session_poll",
        "windows_event_id": login_boundary.get("event_id") if login_boundary else None,
        "windows_event_record_id": login_boundary.get("event_record_id") if login_boundary else None,
        "windows_logon_type": login_boundary.get("logon_type") if login_boundary else None,
        "latest_logout_timestamp": logout_event.get("event_timestamp") if logout_event else None,
        "latest_logout_event_id": logout_event.get("event_id") if logout_event else None,
        "latest_logout_event_record_id": logout_event.get("event_record_id") if logout_event else None,
        "latest_unlock_timestamp": unlock_event.get("event_timestamp") if unlock_event else None,
        "latest_unlock_event_id": unlock_event.get("event_id") if unlock_event else None,
        "latest_unlock_event_record_id": unlock_event.get("event_record_id") if unlock_event else None,
        "device_status": get_device_status(),
        "collection_timestamp": get_login_timestamp(),
    }
    
    logger.info(
        f"Session info collected for user: {session_info.get('username')} "
        f"on hostname: {session_info.get('hostname')}"
    )
    
    return session_info


# ============================================================================
# CLI Testing (when run directly)
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  Asset Sentinel Session Manager - Test Output")
    print("=" * 70 + "\n")
    
    session_info = get_current_session_info()
    
    for key, value in session_info.items():
        print(f"  {key:.<30} {value}")
    
    print("\n" + "=" * 70 + "\n")

