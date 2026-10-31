from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


def utc_now():
    return datetime.now(timezone.utc)


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(64), primary_key=True, index=True)
    correlation_id = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(String(64), nullable=False)
    customer_name = Column(String(128), nullable=False)
    customer_email = Column(String(128), nullable=False)
    product_sku = Column(String(64), nullable=False)
    product_name = Column(String(256), nullable=False)
    order_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    current_stage = Column(String(32), nullable=False, default="CUSTOMER_ORDER")
    order_status = Column(String(32), nullable=False, default="PENDING", index=True)
    payment_status = Column(String(32), nullable=False, default="PENDING")
    inventory_status = Column(String(32), nullable=False, default="PENDING")
    fulfilment_status = Column(String(32), nullable=False, default="PENDING")
    is_demo_order = Column(Boolean, nullable=False, default=False, index=True)
    demo_session_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan", order_by="OrderEvent.timestamp")
    incidents = relationship("Incident", back_populates="order", cascade="all, delete-orphan")


class OrderEvent(Base):
    __tablename__ = "order_events"

    event_id = Column(String(64), primary_key=True, index=True)
    order_id = Column(String(64), ForeignKey("orders.order_id"), nullable=False, index=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    stage = Column(String(32), nullable=False)
    service_name = Column(String(64), nullable=False)
    endpoint = Column(String(256), nullable=False)
    http_method = Column(String(10), nullable=False, default="POST")
    http_status = Column(Integer, nullable=False)
    duration_ms = Column(Integer, nullable=False, default=0)
    event_status = Column(String(32), nullable=False)  # SUCCESS, FAILED, DELAYED
    payload_summary = Column(Text, nullable=True)  # Serialized JSON string
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)

    order = relationship("Order", back_populates="events")


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(64), primary_key=True, index=True)
    order_id = Column(String(64), ForeignKey("orders.order_id"), nullable=False, index=True)
    stage = Column(String(32), nullable=False)
    service_name = Column(String(64), nullable=False)
    failure_category = Column(String(32), nullable=False, index=True)  # API_ERROR, ORDER_DELAY, ORDER_REJECTION
    failure_type = Column(String(64), nullable=False)  # HTTP_503, SLA_BREACH, OUT_OF_STOCK
    incident_status = Column(String(32), nullable=False, default="DETECTED", index=True)  # DETECTED, ANALYZING, PENDING_APPROVAL, RESOLVING, RESOLVED, ESCALATED, REJECTED
    severity = Column(String(16), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    retry_count = Column(Integer, nullable=False, default=0)  # 0 initial, 1, 2, 3 retries
    max_retries = Column(Integer, nullable=False, default=3)
    detected_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    resolved_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="incidents")
    rca_report = relationship("RCAReport", back_populates="incident", uselist=False, cascade="all, delete-orphan")
    resolution_actions = relationship("ResolutionAction", back_populates="incident", cascade="all, delete-orphan")
    approvals = relationship("OperatorApproval", back_populates="incident", cascade="all, delete-orphan")


class RCAReport(Base):
    __tablename__ = "rca_reports"

    rca_id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    failure_category = Column(String(32), nullable=False)
    affected_service = Column(String(64), nullable=False)
    observed_evidence = Column(Text, nullable=False)  # Serialized JSON array of strings
    probable_root_cause = Column(Text, nullable=False)
    evidence_strength = Column(String(16), nullable=False)  # HIGH, MEDIUM, LOW
    corroborating_signals_count = Column(Integer, nullable=False, default=1)
    recommended_action = Column(String(64), nullable=False)
    risk_level = Column(String(16), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    explanation = Column(Text, nullable=False)
    model_source = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    incident = relationship("Incident", back_populates="rca_report")


class ResolutionAction(Base):
    __tablename__ = "resolution_actions"

    action_id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    order_id = Column(String(64), ForeignKey("orders.order_id"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)  # RETRY_WITH_BACKOFF, OPERATOR_ACTION
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)  # Retry execution number: 1, 2, or 3
    backoff_delay_sec = Column(Integer, nullable=False, default=0)
    execution_status = Column(String(32), nullable=False, default="PENDING")  # PENDING, EXECUTING, VERIFYING, SUCCEEDED, FAILED
    payload_diff = Column(Text, nullable=True)
    execution_response = Column(Text, nullable=True)
    verification_passed = Column(Boolean, nullable=False, default=False)
    verification_details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="resolution_actions")


class OperatorApproval(Base):
    __tablename__ = "operator_approvals"

    approval_id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    order_id = Column(String(64), ForeignKey("orders.order_id"), nullable=False, index=True)
    selected_action = Column(String(64), nullable=False)
    action_parameters = Column(Text, nullable=True)  # Serialized JSON string
    risk_level = Column(String(16), nullable=False)
    decision = Column(String(32), nullable=False, default="PENDING", index=True)  # PENDING, APPROVED, REJECTED
    operator_id = Column(String(64), nullable=True)
    operator_name = Column(String(128), nullable=True)
    operator_notes = Column(Text, nullable=True)
    requested_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    decided_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    order_id = Column(String(64), nullable=True, index=True)
    incident_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor_type = Column(String(32), nullable=False)  # SYSTEM, AI_AGENT, OPERATOR, SIMULATOR
    actor_id = Column(String(64), nullable=False)
    summary = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # Serialized JSON string
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)


class SystemPolicy(Base):
    __tablename__ = "system_policies"

    policy_key = Column(String(64), primary_key=True)
    policy_name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False)  # SLA, RETRY, RISK, AI
    value_type = Column(String(16), nullable=False)  # INTEGER, FLOAT, STRING, BOOLEAN
    policy_value = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

