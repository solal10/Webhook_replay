import enum
from datetime import UTC, datetime
from datetime import timezone as tz

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    return datetime.now(tz.utc)


class DeliveryStatus(str, enum.Enum):
    delivered = "delivered"
    failed = "failed"


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    stripe_signing_secret = Column(String, nullable=True)

    api_keys = relationship("ApiKey", back_populates="tenant")
    targets = relationship("Target", back_populates="tenant")
    events = relationship("Event", back_populates="tenant")


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    hashed_key = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="api_keys")


class Target(Base):
    __tablename__ = "targets"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    url = Column(String, nullable=False)
    provider = Column(String, default="stripe")

    tenant = relationship("Tenant", back_populates="targets")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    provider = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload_path = Column(String, nullable=False)
    hash = Column(String, nullable=False)  # Unique identifier for the event
    content_hash = Column(
        String, nullable=False
    )  # Hash of the raw content, used for duplicate detection
    duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    deliveries = relationship("Delivery", back_populates="event")
    tenant = relationship("Tenant", back_populates="events")


class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    status = Column(Enum(DeliveryStatus), nullable=False)
    attempt = Column(Integer, default=1)
    code = Column(Integer)
    logged_at = Column(DateTime, default=utc_now)

    event = relationship("Event", back_populates="deliveries")
