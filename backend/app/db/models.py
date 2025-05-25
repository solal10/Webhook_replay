import enum
from datetime import UTC, datetime
from datetime import timezone as tz

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    return datetime.now(tz.utc)


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
    headers = Column(JSON, nullable=True)

    tenant = relationship("Tenant", back_populates="targets")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    sha256 = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    tenant = relationship("Tenant", back_populates="events")

    __table_args__ = (Index("ix_event_unique", "tenant_id", "sha256"),)


class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    status = Column(Integer, nullable=False)
    response = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    event = relationship("Event")
