from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
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
        Index("idx_sessions_hostname_recorded_at", "hostname", recorded_at.desc()),
        Index("idx_sessions_username_recorded_at", "username", recorded_at.desc()),
        Index("idx_sessions_active", "active"),
        Index("idx_sessions_event_type", "event_type"),
        Index("idx_sessions_login_timestamp", login_timestamp.desc()),
        Index("idx_sessions_windows_event_record_id", "windows_event_record_id"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(BigInteger, primary_key=True)
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
        Index("idx_alerts_hostname_timestamp", "hostname", timestamp.desc()),
        Index("idx_alerts_severity_timestamp", "severity", timestamp.desc()),
        Index("idx_alerts_alert_type", "alert_type"),
        Index("idx_alerts_details_gin", "details", postgresql_using="gin"),
        Index("idx_alerts_unacknowledged", "acknowledged", postgresql_where=(acknowledged.is_(False))),
    )


class ActiveApplication(Base):
    __tablename__ = "active_applications"

    id = Column(BigInteger, primary_key=True)
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
        Index("idx_active_applications_hostname_timestamp", "hostname", timestamp.desc()),
        Index("idx_active_applications_username_timestamp", "username", timestamp.desc()),
        Index("idx_active_applications_timestamp", timestamp.desc()),
    )


class ActiveApplicationHistory(Base):
    __tablename__ = "active_application_history"

    id = Column(BigInteger, primary_key=True)
    hostname = Column(String(255), nullable=False)
    username = Column(String(255))
    application = Column(String(512))
    window_title = Column(Text)
    process_path = Column(Text)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_active_application_history_hostname_timestamp", "hostname", timestamp.desc()),
        Index("idx_active_application_history_username_timestamp", "username", timestamp.desc()),
    )


class HardwareChange(Base):
    __tablename__ = "hardware_changes"

    id = Column(BigInteger, primary_key=True)
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
        Index("idx_hardware_changes_hostname_detected_at", "hostname", detected_at.desc()),
        Index("idx_hardware_changes_type_detected_at", "change_type", detected_at.desc()),
        Index("idx_hardware_changes_alert_id", "alert_id"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    email = Column(String(320), nullable=False)
    username = Column(String(255), nullable=False)
    password_hash = Column(Text)
    display_name = Column(String(255))
    role = Column(String(50), nullable=False, default="Admin")
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
        CheckConstraint("role IN ('Admin', 'IT Admin', 'Viewer')", name="chk_users_role"),
        Index("idx_users_role", "role"),
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
