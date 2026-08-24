from app.database.db import Base, engine

# Import every model so SQLAlchemy knows about every table.
from app.models.user import User
from app.models.complaint import Complaint
from app.models.agent import Agent
from app.models.team import Team
from app.models.ticket_event import TicketEvent


def create_tables():
    Base.metadata.create_all(
        bind=engine
    )