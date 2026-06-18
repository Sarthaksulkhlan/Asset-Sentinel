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
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import os

try:
    import wmi
except ImportError:
    wmi = None

try:
    import psutil
except ImportError:
    psutil = None

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger("session_manager")


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
        return None
    
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


def get_device_status() -> str:
    """
    Get the current device status.
    
    Returns:
        str: 'Online' if user is logged in, 'Offline' otherwise
    """
    username = get_current_username()
    return "Online" if username else "Offline"


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
    session_info = {
        "username": get_current_username(),
        "hostname": get_current_hostname(),
        "ip_address": get_current_ip_address(),
        "session_id": get_session_id_via_wmi(),
        "login_timestamp": get_login_timestamp(),
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
