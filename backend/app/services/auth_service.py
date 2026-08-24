from sqlalchemy.orm import Session
from app.models.user import User
from app.models.agent import Agent


def login_user(email: str, password: str, db: Session):
    user = db.query(User).filter(User.email == email, User.password == password).first()
    if user:
        return user
    return db.query(Agent).filter(Agent.email == email, Agent.password == password, Agent.active.is_(True)).first()
