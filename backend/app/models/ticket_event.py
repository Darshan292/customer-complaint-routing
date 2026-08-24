from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from app.database.db import Base


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    actor_id = Column(Integer, nullable=True)
    actor_role = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    from_value = Column(String, nullable=True)
    to_value = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
