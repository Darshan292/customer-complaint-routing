from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.database.db import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    recipient_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    recipient_role = Column(
        String,
        nullable=False,
        index=True,
    )

    notification_type = Column(
        String,
        nullable=False,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    ticket_id = Column(
        Integer,
        ForeignKey("complaints.id"),
        nullable=True,
        index=True,
    )

    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    read_at = Column(
        DateTime,
        nullable=True,
    )
