from sqlalchemy import Boolean, Column, Integer, String
from app.database.db import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    queue = Column(String, unique=True, nullable=False)
    active = Column(Boolean, default=True)
    default_capacity = Column(Integer, default=20)
