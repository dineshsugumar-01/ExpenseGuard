from datetime import datetime
import uuid
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Date,
    Text,
    JSON,
    ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), default="auditor", nullable=False)  # employee, auditor, admin
    firefly_account_id = Column(Integer, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transactions = relationship("TransactionCache", back_populates="employee")
    reviewed_flags = relationship("Flag", back_populates="reviewer")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    firefly_group_id = Column(String(100), unique=True, index=True, nullable=False)
    event_type = Column(String(100), default="STORE_TRANSACTION", nullable=False)
    payload_json = Column(JSON, nullable=False)
    status = Column(String(50), default="received", nullable=False)  # received, processed, duplicate, failed
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TransactionCache(Base):
    __tablename__ = "transactions_cache"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    firefly_group_id = Column(String(100), unique=True, index=True, nullable=False)
    journal_id = Column(Integer, nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String(100), default="Uncategorized", nullable=False, index=True)
    vendor = Column(String(255), default="Unknown", nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=True, index=True)
    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="transactions")
    score = relationship("Score", back_populates="transaction", uselist=False)


class Score(Base):
    __tablename__ = "scores"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    firefly_group_id = Column(String(100), ForeignKey("transactions_cache.firefly_group_id"), unique=True, index=True, nullable=False)
    risk_score = Column(Float, nullable=False, index=True)  # 0 to 100
    tier = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH
    model_score = Column(Float, default=0.0, nullable=False)
    rule_boost = Column(Float, default=0.0, nullable=False)
    model_version_id = Column(String(36), ForeignKey("model_versions.id"), nullable=True)
    features_json = Column(JSON, nullable=True)
    reasons_json = Column(JSON, nullable=True)
    contributions_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    transaction = relationship("TransactionCache", back_populates="score")
    model_version = relationship("ModelVersion", back_populates="scores")
    rule_hits = relationship("RuleHit", back_populates="score", cascade="all, delete-orphan")
    flag = relationship("Flag", back_populates="score", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="score", cascade="all, delete-orphan")


class RuleHit(Base):
    __tablename__ = "rule_hits"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    score_id = Column(String(36), ForeignKey("scores.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False, index=True)
    severity = Column(Integer, default=10, nullable=False)
    message = Column(Text, nullable=False)
    details_json = Column(JSON, nullable=True)

    score = relationship("Score", back_populates="rule_hits")


class Flag(Base):
    __tablename__ = "flags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    score_id = Column(String(36), ForeignKey("scores.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    status = Column(String(50), default="open", nullable=False, index=True)  # open, confirmed, false_alarm
    reviewed_by = Column(String(36), ForeignKey("employees.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    score = relationship("Score", back_populates="flag")
    reviewer = relationship("Employee", back_populates="reviewed_flags")


class RulesConfig(Base):
    __tablename__ = "rules_config"

    rule_id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    severity = Column(Integer, default=15, nullable=False)
    params_json = Column(JSON, default=dict, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version_tag = Column(String(100), unique=True, nullable=False)
    trained_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    training_rows = Column(Integer, default=0, nullable=False)
    models_included = Column(JSON, default=list, nullable=False)
    contamination = Column(Float, default=0.05, nullable=False)
    metrics_json = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    file_path = Column(String(500), nullable=True)

    scores = relationship("Score", back_populates="model_version")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    score_id = Column(String(36), ForeignKey("scores.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(50), default="email", nullable=False)  # email, slack
    destination = Column(String(255), nullable=False)
    status = Column(String(50), default="sent", nullable=False)  # sent, failed
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    score = relationship("Score", back_populates="alerts")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_id = Column(String(36), nullable=True)
    actor_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    changes_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
