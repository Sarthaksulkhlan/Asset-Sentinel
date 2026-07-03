import logging
from typing import Any, Dict, Optional

from collect_hardware import collect_hardware
from login_tracker import detect_login
from storage import append_alert, list_assets, record_hardware_change, resolve_device_uid, upsert_asset


logger = logging.getLogger("asset_sentinel.telemetry")


def _find_existing_asset(device_uid: str, hostname: Optional[str]) -> Optional[Dict[str, Any]]:
    try:
        for asset in list_assets():
            if asset.get("device_uid") == device_uid:
                return asset
    except Exception as exc:
        logger.exception("Could not read existing assets before telemetry bootstrap: %s", exc)
    return None


def _record_change_if_needed(existing: Optional[Dict[str, Any]], current: Dict[str, Any]) -> None:
    if not existing:
        return

    hostname = current.get("hostname") or existing.get("hostname") or "Unknown"
    detected_at = current.get("collected_at")

    previous_ram = existing.get("ram_total_gb")
    current_ram = current.get("ram_total_gb")
    if previous_ram is not None and current_ram is not None and float(previous_ram) != float(current_ram):
        details = {
            "previous_ram_gb": previous_ram,
            "current_ram_gb": current_ram,
            "previous_snapshot_time": existing.get("collected_at"),
            "current_snapshot_time": detected_at,
        }
        append_alert("RAM_CHANGE", hostname, "HIGH", details, detected_at)
        record_hardware_change(
            hostname=hostname,
            change_type="RAM_CHANGE",
            severity="HIGH",
            previous_value={"ram_total_gb": previous_ram},
            current_value={"ram_total_gb": current_ram},
            difference={"changed": True},
            detected_at=detected_at,
        )
        logger.warning("RAM change recorded for %s: %s -> %s", hostname, previous_ram, current_ram)

    motherboard_fields = ("bios_serial", "baseboard_serial", "uuid", "baseboard_product")
    differences = {}
    for field in motherboard_fields:
        previous_value = existing.get(field)
        current_value = current.get(field)
        if not previous_value or not current_value:
            continue
        previous_norm = str(previous_value).strip().lower()
        current_norm = str(current_value).strip().lower()
        if previous_norm != current_norm:
            differences[field] = {"previous": previous_value, "current": current_value}
    if differences:
        append_alert("MOTHERBOARD_CHANGE", hostname, "CRITICAL", differences, detected_at)
        record_hardware_change(
            hostname=hostname,
            change_type="MOTHERBOARD_CHANGE",
            severity="CRITICAL",
            previous_value={field: values["previous"] for field, values in differences.items()},
            current_value={field: values["current"] for field, values in differences.items()},
            difference=differences,
            detected_at=detected_at,
        )
        logger.critical("Motherboard identity change recorded for %s: %s", hostname, differences)


def bootstrap_local_telemetry() -> bool:
    logger.info("Telemetry bootstrap starting: Windows/WMI -> agent -> PostgreSQL")
    try:
        hardware = collect_hardware()
    except Exception as exc:
        logger.exception("Telemetry bootstrap failed during hardware collection: %s", exc)
        return False

    hostname = hardware.get("hostname")
    device_uid = resolve_device_uid(hardware)
    logger.info(
        "Collected local hardware telemetry: hostname=%s uid=%s method=%s errors=%s",
        hostname,
        device_uid,
        hardware.get("collection_method"),
        len(hardware.get("collection_errors") or []),
    )

    if not hostname:
        logger.error("Local device was not registered because hostname collection returned empty.")
        return False

    existing = _find_existing_asset(device_uid, hostname)
    try:
        _record_change_if_needed(existing, hardware)
        upsert_asset(hardware)
        logger.info(
            "Local device %s %s in PostgreSQL assets table.",
            hostname,
            "updated" if existing else "created",
        )
    except Exception as exc:
        logger.exception("Could not upsert local device into PostgreSQL: %s", exc)
        return False

    try:
        login_record = detect_login()
        if login_record:
            logger.info("Windows login session recorded for %s.", login_record.get("username"))
        else:
            logger.info("Windows login tracker ran; no new login boundary detected.")
    except Exception as exc:
        logger.exception("Login tracking failed during telemetry bootstrap: %s", exc)

    logger.info("Telemetry data flow verified through PostgreSQL bootstrap for host %s.", hostname)
    return True
