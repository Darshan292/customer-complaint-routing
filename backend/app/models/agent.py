from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)

from app.database.db import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    password = Column(
        String,
        nullable=False,
    )

    role = Column(
        String,
        nullable=False,
        default="agent",
    )

    team = Column(
        String,
        nullable=False,
        index=True,
    )

    skills = Column(
        String,
        default="",
    )

    experience_years = Column(
        Float,
        default=0,
    )

    capacity = Column(
        Integer,
        default=10,
        nullable=False,
    )

    max_concurrent_tickets = Column(
        Integer,
        default=10,
        nullable=False,
    )

    active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    availability_status = Column(
        String,
        default="AVAILABLE",
        nullable=False,
        index=True,
    )

    timezone = Column(
        String,
        default="Asia/Kolkata",
        nullable=False,
    )

    shift_start = Column(
        String,
        default="09:00",
        nullable=False,
    )

    shift_end = Column(
        String,
        default="18:00",
        nullable=False,
    )

    work_days = Column(
        String,
        default="0,1,2,3,4",
        nullable=False,
    )

    auto_assignment_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    on_call_enabled = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_status_change_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )