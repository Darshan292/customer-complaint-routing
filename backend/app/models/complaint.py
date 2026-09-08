from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from app.database.db import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False, index=True)
    customer_tier = Column(String, default="Standard", index=True)
    complaint_text = Column(Text, nullable=False)

    category = Column(String, index=True)
    subcategory = Column(String)
    sentiment = Column(String)
    emotion = Column(String)
    business_impact = Column(String)
    customer_intent = Column(String)
    summary = Column(Text)
    confidence = Column(Float)
    keywords = Column(Text)
    routing_reason = Column(Text)

    # Priority can come from the customer, AI, or a final admin override.
    priority_source = Column(String, default="AI")
    priority_score = Column(Float, default=0)
    priority_level = Column(String, default="Medium", index=True)

    assigned_team = Column(String, index=True)
    assigned_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    assigned_agent_name = Column(String, nullable=True)
    queue = Column(String)

    # Temporary integration workflow marker.
    request_type = Column(String, nullable=True, index=True)

    status = Column(String, default="OPEN", index=True)
    escalation_required = Column(Boolean, default=False)
    # --------------------------------------------------
    # SLA
    # --------------------------------------------------

    sla_hours = Column(
        Integer
    )

    sla_deadline = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    # First-response SLA
    first_response_sla_minutes = Column(
        Integer,
        default=30,
        nullable=False,
    )

    first_response_deadline = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    first_response_at = Column(
        DateTime,
        nullable=True,
    )

    # Resolution SLA pause tracking
    sla_paused_at = Column(
        DateTime,
        nullable=True,
    )

    sla_total_paused_seconds = Column(
        Float,
        default=0,
        nullable=False,
    )

    resolved_at = Column(
        DateTime,
        nullable=True,
    )

    # --------------------------------------------------
    # Escalation
    # --------------------------------------------------

    escalation_level = Column(
        Integer,
        default=0,
        nullable=False,
    )

    escalated_at = Column(
        DateTime,
        nullable=True,
    )

    escalation_reason = Column(
        String,
        nullable=True,
    )

    escalation_owner = Column(
        String,
        nullable=True,
    )

    escalation_count = Column(
        Integer,
        default=0,
        nullable=False,
    )
    assignment_score = Column(Float, nullable=True)
    assignment_explanation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
