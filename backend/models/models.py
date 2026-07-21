from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import String

from database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    device_uid = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(INET)
    mac_address = Column(String(32))
    bios_serial = Column(String(255))
    baseboard_serial = Column(String(255))
    uuid = Column(UUID(as_uuid=True))
    composite_id = Column(String(128))
    cpu_name = Column(Text)
    ram_total_gb = Column(Numeric(10, 2))
    baseboard_manufacturer = Column(String(255))
    baseboard_product = Column(String(255))
    windows_version = Column(String(255))
    current_website = Column(Text)
    active_window_title = Column(Text)
    active_process_path = Column(Text)
    active_process_name = Column(String(512))
    cpu_usage_percent = Column(Numeric(5, 2))
    ram_usage_percent = Column(Numeric(5, 2))
    status = Column(String(20), nullable=False, default="Offline")
    last_seen = Column(DateTime(timezone=True))
    collection_method = Column(String(50), nullable=False, default="none")
    collection_errors = Column(JSONB, nullable=False, default=list)
    collected_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "collection_method IN ('bios_serial', 'baseboard_serial', 'uuid', 'composite', 'none')",
            name="chk_assets_collection_method",
        ),
        CheckConstraint("status IN ('Online', 'Idle', 'Offline', 'Overload')", name="chk_assets_status"),
        UniqueConstraint("device_uid", name="uq_assets_device_uid"),
        UniqueConstraint("hostname", "collected_at", name="uq_assets_hostname_collected_at"),
        Index("idx_assets_company_id", "company_id"),
        Index("idx_assets_device_uid", "device_uid"),
        Index("idx_assets_hostname_collected_at", "hostname", collected_at.desc()),
        Index("idx_assets_last_seen", last_seen.desc()),
        Index("idx_assets_bios_serial", "bios_serial"),
        Index("idx_assets_baseboard_serial", "baseboard_serial"),
        Index("idx_assets_uuid", "uuid"),
        Index("idx_assets_composite_id", "composite_id"),
        Index("idx_assets_collected_at", collected_at.desc()),
    )


class SessionRecord(Base):
    __tablename__ = "sessions"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    event_type = Column(String(20), nullable=False)
    username = Column(String(255))
    hostname = Column(String(255), nullable=False)
    ip_address = Column(INET)
    session_id = Column(String(255))
    login_timestamp = Column(DateTime(timezone=True))
    logout_timestamp = Column(DateTime(timezone=True))
    session_duration = Column(String(50))
    active = Column(Boolean, nullable=False, default=False)
    device_status = Column(String(20))
    last_seen = Column(DateTime(timezone=True))
    login_source = Column(String(50))
    windows_event_id = Column(String(20))
    windows_event_record_id = Column(String(255))
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("event_type IN ('LOGIN', 'LOGOUT')", name="chk_sessions_event_type"),
        CheckConstraint(
            "device_status IS NULL OR device_status IN ('Online', 'Offline')",
            name="chk_sessions_device_status",
        ),
        UniqueConstraint(
            "event_type",
            "hostname",
            "username",
            "session_id",
            "recorded_at",
            name="uq_sessions_event_identity",
        ),
        Index("idx_sessions_company_id", "company_id"),
        Index("idx_sessions_hostname_recorded_at", "hostname", recorded_at.desc()),
        Index("idx_sessions_username_recorded_at", "username", recorded_at.desc()),
        Index("idx_sessions_active", "active"),
        Index("idx_sessions_event_type", "event_type"),
        Index("idx_sessions_login_timestamp", login_timestamp.desc()),
        Index("idx_sessions_windows_event_record_id", "windows_event_record_id"),
        Index(
            "uq_sessions_hostname_windows_event_record_id",
            "hostname",
            "windows_event_record_id",
            unique=True,
            postgresql_where=windows_event_record_id.is_not(None),
        ),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    alert_type = Column(String(100), nullable=False)
    hostname = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    acknowledged = Column(Boolean, nullable=False, default=False)
    acknowledged_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    hardware_changes = relationship("HardwareChange", back_populates="alert")

    __table_args__ = (
        CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="chk_alerts_severity"),
        UniqueConstraint("alert_type", "hostname", "severity", "timestamp", name="uq_alerts_event_identity"),
        Index("idx_alerts_company_id", "company_id"),
        Index("idx_alerts_hostname_timestamp", "hostname", timestamp.desc()),
        Index("idx_alerts_severity_timestamp", "severity", timestamp.desc()),
        Index("idx_alerts_alert_type", "alert_type"),
        Index("idx_alerts_details_gin", "details", postgresql_using="gin"),
        Index("idx_alerts_unacknowledged", "acknowledged", postgresql_where=(acknowledged.is_(False))),
    )


class ActiveApplication(Base):
    __tablename__ = "active_applications"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    hostname = Column(String(255), nullable=False)
    username = Column(String(255))
    application_name = Column(String(512))
    executable_name = Column(String(512))
    window_title = Column(Text)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "hostname",
            "username",
            "executable_name",
            "window_title",
            "timestamp",
            name="uq_active_applications_signature",
        ),
        Index("idx_active_applications_company_id", "company_id"),
        Index("idx_active_applications_hostname_timestamp", "hostname", timestamp.desc()),
        Index("idx_active_applications_username_timestamp", "username", timestamp.desc()),
        Index("idx_active_applications_timestamp", timestamp.desc()),
    )


class ActiveApplicationHistory(Base):
    __tablename__ = "active_application_history"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    hostname = Column(String(255), nullable=False)
    username = Column(String(255))
    application = Column(String(512))
    window_title = Column(Text)
    process_path = Column(Text)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_active_application_history_company_id", "company_id"),
        Index("idx_active_application_history_hostname_timestamp", "hostname", timestamp.desc()),
        Index("idx_active_application_history_username_timestamp", "username", timestamp.desc()),
    )


class ApplicationUsageSegment(Base):
    __tablename__ = "application_usage_segments"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    device_id = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    username = Column(String(255))
    application_name = Column(String(512), nullable=False)
    window_title = Column(Text)
    process_path = Column(Text)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    active_duration = Column(Integer, nullable=False, default=0)
    idle_duration = Column(Integer, nullable=False, default=0)
    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("device_id", "application_name", "start_time", "end_time", name="uq_application_usage_segments_identity"),
        Index("idx_application_usage_segments_company_id", "company_id"),
        Index("idx_application_usage_segments_device_date", "device_id", "date"),
        Index("idx_application_usage_segments_hostname_start", "hostname", start_time.desc()),
        Index("idx_application_usage_segments_application", "application_name"),
    )


class ApplicationUsageDaily(Base):
    __tablename__ = "application_usage_daily"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    date = Column(DateTime(timezone=True), nullable=False)
    hostname = Column(String(255), nullable=False)
    username = Column(String(255))
    application_name = Column(String(512), nullable=False)
    window_title = Column(Text)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    total_foreground_seconds = Column(Integer, nullable=False, default=0)
    active_seconds = Column(Integer, nullable=False, default=0)
    idle_seconds = Column(Integer, nullable=False, default=0)
    locked_seconds = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("date", "hostname", "username", "application_name", "window_title", name="uq_application_usage_daily_app"),
        Index("idx_application_usage_daily_company_id", "company_id"),
        Index("idx_application_usage_daily_host_date", "hostname", "date"),
        Index("idx_application_usage_daily_app", "application_name"),
    )


class ActivitySession(Base):
    __tablename__ = "activity_sessions"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    hostname = Column(String(255), nullable=False)
    username = Column(String(255))
    app_name = Column(String(512), nullable=False)
    window_title = Column(Text)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    total_seconds = Column(Integer, nullable=False, default=0)
    active_seconds = Column(Integer, nullable=False, default=0)
    idle_seconds = Column(Integer, nullable=False, default=0)
    locked_seconds = Column(Integer, nullable=False, default=0)
    created_date = Column(DateTime(timezone=True), nullable=False)
    last_state = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("last_state IN ('ACTIVE', 'IDLE', 'LOCKED')", name="chk_activity_sessions_last_state"),
        Index("idx_activity_sessions_company_id", "company_id"),
        Index("idx_activity_sessions_host_created_date", "hostname", "created_date"),
        Index("idx_activity_sessions_host_end", "hostname", end_time.desc()),
        Index("idx_activity_sessions_app", "app_name"),
    )


class HardwareChange(Base):
    __tablename__ = "hardware_changes"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    hostname = Column(String(255), nullable=False)
    change_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    previous_asset_id = Column(BigInteger, ForeignKey("assets.id", ondelete="SET NULL"))
    current_asset_id = Column(BigInteger, ForeignKey("assets.id", ondelete="SET NULL"))
    previous_value = Column(JSONB, nullable=False, default=dict)
    current_value = Column(JSONB, nullable=False, default=dict)
    difference = Column(JSONB, nullable=False, default=dict)
    detected_at = Column(DateTime(timezone=True), nullable=False)
    alert_id = Column(BigInteger, ForeignKey("alerts.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    alert = relationship("Alert", back_populates="hardware_changes")

    __table_args__ = (
        CheckConstraint(
            "change_type IN ('RAM_CHANGE', 'MOTHERBOARD_CHANGE')",
            name="chk_hardware_changes_type",
        ),
        CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="chk_hardware_changes_severity"),
        UniqueConstraint(
            "hostname",
            "change_type",
            "previous_asset_id",
            "current_asset_id",
            name="uq_hardware_changes_snapshot_pair",
        ),
        Index("idx_hardware_changes_company_id", "company_id"),
        Index("idx_hardware_changes_hostname_detected_at", "hostname", detected_at.desc()),
        Index("idx_hardware_changes_type_detected_at", "change_type", detected_at.desc()),
        Index("idx_hardware_changes_alert_id", "alert_id"),
    )


class Company(Base):
    __tablename__ = "companies"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(255), nullable=False)
    website = Column(String(512))
    industry = Column(String(120))
    company_size = Column(String(80))
    country = Column(String(120))
    plan = Column(String(80), nullable=False, default="Trial", server_default="Trial")
    status = Column(String(30), nullable=False, default="Active", server_default="Active")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("name", name="uq_companies_name"),
        CheckConstraint("status IN ('Active', 'Suspended')", name="chk_companies_status"),
        Index("idx_companies_status", "status"),
        Index("idx_companies_created_at", created_at.desc()),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    email = Column(String(320), nullable=False)
    username = Column(String(255), nullable=False)
    password_hash = Column(Text)
    display_name = Column(String(255))
    role = Column(String(50), nullable=False, default="Admin")
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    is_active = Column(Boolean, nullable=False, default=True)
    external_provider = Column(String(100))
    external_subject = Column(String(255))
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("external_provider", "external_subject", name="uq_users_external_identity"),
        CheckConstraint("role IN ('SUPER_ADMIN', 'COMPANY_ADMIN', 'Super Admin', 'Admin', 'IT Admin', 'Viewer')", name="chk_users_role"),
        Index("idx_users_role", "role"),
        Index("idx_users_company_id", "company_id"),
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_external_identity", "external_provider", "external_subject"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(128), nullable=False)
    jwt_id = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        UniqueConstraint("jwt_id", name="uq_refresh_tokens_jwt_id"),
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_expires_at", expires_at),
    )


class PasswordResetOtp(Base):
    __tablename__ = "password_reset_otps"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    otp_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0)
    verified = Column(Boolean, nullable=False, default=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    verified_at = Column(DateTime(timezone=True))
    used_at = Column(DateTime(timezone=True))

    user = relationship("User")

    __table_args__ = (
        Index("idx_password_reset_otps_user_created", "user_id", created_at.desc()),
        Index("idx_password_reset_otps_expires_at", expires_at),
    )


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    company_name = Column(String(255), nullable=False)
    company_website = Column(String(512))
    industry = Column(String(120), nullable=False)
    company_size = Column(String(80), nullable=False)
    country = Column(String(120), nullable=False)
    full_name = Column(String(255), nullable=False)
    work_email = Column(String(320), nullable=False)
    mobile_number = Column(String(40), nullable=False)
    job_title = Column(String(160), nullable=False)
    department = Column(String(160), nullable=False)
    username = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)
    terms_accepted = Column(Boolean, nullable=False, default=False)
    privacy_accepted = Column(Boolean, nullable=False, default=False)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("work_email", name="uq_admin_users_work_email"),
        UniqueConstraint("username", name="uq_admin_users_username"),
        Index("idx_admin_users_company_id", "company_id"),
        Index("idx_admin_users_company_name", "company_name"),
        Index("idx_admin_users_created_at", created_at.desc()),
    )


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(BigInteger, primary_key=True)
    ticket_number = Column(String(40), nullable=False)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    created_by_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    category = Column(String(120), nullable=False)
    priority = Column(String(20), nullable=False, default="MEDIUM")
    description = Column(Text, nullable=False)
    related_device = Column(String(255))
    status = Column(String(30), nullable=False, default="OPEN")
    admin_response = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))

    company = relationship("Company")
    created_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("ticket_number", name="uq_support_tickets_ticket_number"),
        CheckConstraint(
            "category IN ('Agent Issue', 'Device Offline', 'Login Tracking Issue', 'Application Monitoring Issue', 'Performance Issue', 'Account Issue', 'Other')",
            name="chk_support_tickets_category",
        ),
        CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="chk_support_tickets_priority"),
        CheckConstraint("status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')", name="chk_support_tickets_status"),
        Index("idx_support_tickets_company_id", "company_id"),
        Index("idx_support_tickets_status", "status"),
        Index("idx_support_tickets_created_at", created_at.desc()),
    )


class EarlyAccessRequest(Base):
    __tablename__ = "early_access_requests"

    id = Column(BigInteger, primary_key=True)
    full_name = Column(String(255))
    email = Column(String(320), nullable=False)
    company = Column(String(255))
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("email", name="uq_early_access_requests_email"),
        Index("idx_early_access_requests_company", "company"),
        Index("idx_early_access_requests_created_at", created_at.desc()),
    )
