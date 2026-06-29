import socket
from datetime import datetime, timezone

from sqlalchemy import text

from database import database_host_for_display, get_db_session
from storage import list_assets


OFFICE_HOSTNAME = "DevrishiBhardwaj"


def main() -> int:
    current_hostname = socket.gethostname()
    with get_db_session() as session:
        duplicate_identity_rows = session.execute(text(
            """
            select coalesce(nullif(lower(uuid::text), ''), nullif(lower(bios_serial), ''),
                           nullif(lower(baseboard_serial), ''), nullif(lower(mac_address), ''),
                           nullif(lower(device_uid), '')) as identity_key,
                   count(*) as row_count,
                   array_agg(hostname order by hostname) as hostnames
            from assets
            group by 1
            having count(*) > 1
            """
        )).mappings().all()
        office_rows = session.execute(
            text("select device_uid, hostname, last_seen from assets where lower(hostname) = lower(:hostname)"),
            {"hostname": OFFICE_HOSTNAME},
        ).mappings().all()
        laptop_rows = session.execute(
            text("select device_uid, hostname, last_seen from assets where lower(hostname) = lower(:hostname)"),
            {"hostname": current_hostname},
        ).mappings().all()
        placeholder_rows = session.execute(text(
            """
            select count(*)
            from active_application_history
            where application in ('Chrome opened', 'VS Code opened', 'Explorer opened', 'Excel opened')
               or window_title ilike '%Awaiting live PostgreSQL%'
            """
        )).scalar()
        session_summary = session.execute(text(
            """
            select hostname,
                   count(*) filter (
                       where event_type = 'LOGIN'
                         and login_source = 'windows_interactive_logon'
                         and (login_timestamp at time zone 'Asia/Kolkata')::date = (now() at time zone 'Asia/Kolkata')::date
                   ) as logins_today_ist,
                   count(*) filter (
                       where event_type = 'LOGIN'
                         and login_source = 'windows_interactive_logon'
                   ) as total_real_logins,
                   count(*) filter (where event_type = 'LOGOUT') as total_logouts
            from sessions
            group by hostname
            order by hostname
            """
        )).mappings().all()

    assets = list_assets()
    print(f"Database host: {database_host_for_display()}")
    print(f"Checked at: {datetime.now(timezone.utc).isoformat()}")
    print(f"Fleet rows returned by API storage layer: {len(assets)}")
    print(f"Current laptop hostname: {current_hostname}; rows: {len(laptop_rows)}")
    print(f"Office hostname: {OFFICE_HOSTNAME}; rows: {len(office_rows)}")
    print(f"Duplicate physical identity groups: {len(duplicate_identity_rows)}")
    print(f"Placeholder active application rows: {placeholder_rows}")
    print("Fleet status:")
    for asset in assets:
        print(f"  {asset.get('hostname')}: {asset.get('status')} last_seen={asset.get('last_seen')} active_app={asset.get('active_application')}")
    print("Countable login summary:")
    for row in session_summary:
        print(f"  {row['hostname']}: today_ist={row['logins_today_ist']} total_real_logins={row['total_real_logins']} logouts={row['total_logouts']}")

    failed = False
    if duplicate_identity_rows:
        failed = True
        print(f"Duplicate identity details: {[dict(row) for row in duplicate_identity_rows]}")
    if len(office_rows) > 1:
        failed = True
        print(f"Office duplicate rows: {[dict(row) for row in office_rows]}")
    if len(laptop_rows) > 1:
        failed = True
        print(f"Laptop duplicate rows: {[dict(row) for row in laptop_rows]}")
    if placeholder_rows:
        failed = True
    if failed:
        return 1

    print("Neon integrity verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
