from app.database.db import SessionLocal, engine, Base
from app.models.user import User
from app.models.agent import Agent
from app.models.team import Team
from app.models.complaint import Complaint
from app.models.ticket_event import TicketEvent

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    teams = [
        ("Technical Support", "TECH-L1", 20),
        ("Finance Operations", "BILLING-L1", 15),
        ("Fraud Investigation", "FRAUD-L1", 10),
        ("Cyber Security", "SECURITY-L1", 10),
        ("Site Reliability", "SRE-L1", 8),
        ("General Support", "GENERAL-L1", 20),
    ]
    for name, queue, cap in teams:
        if not db.query(Team).filter(Team.name == name).first():
            db.add(Team(name=name, queue=queue, default_capacity=cap))

    users = [
        ("Admin", "admin@example.com", "password123", "admin"),
        ("John", "john@gmail.com", "123456", "customer"),
        ("Ava", "ava@gmail.com", "123456", "customer"),
        ("Smith", "smith@gmail.com", "123456", "customer"),
    ]
    for name,email,pw,role in users:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(name=name,email=email,password=pw,role=role))

    agents = [
        {
            "name": "Alex Morgan",
            "email": "alex@support.example.com",
            "password": "agent123",
            "team": "Technical Support",
            "skills": "technical,bug,api,integration",
            "experience_years": 7,
            "capacity": 12,
            "max_concurrent_tickets": 8,
            "role": "agent",
            "availability_status": "AVAILABLE",
            "timezone": "Asia/Kolkata",
            "shift_start": "09:00",
            "shift_end": "18:00",
            "work_days": "0,1,2,3,4",
            "auto_assignment_enabled": True,
        },
        {
            "name": "Priya Nair",
            "email": "priya@support.example.com",
            "password": "agent123",
            "team": "Technical Support",
            "skills": "technical,workday,api,sql",
            "experience_years": 4,
            "capacity": 8,
            "max_concurrent_tickets": 6,
            "role": "agent",
            "availability_status": "AVAILABLE",
            "timezone": "Asia/Kolkata",
            "shift_start": "10:00",
            "shift_end": "19:00",
            "work_days": "0,1,2,3,4",
            "auto_assignment_enabled": True,
        },
        {
            "name": "Daniel Chen",
            "email": "daniel@support.example.com",
            "password": "agent123",
            "team": "Technical Support",
            "skills": "technical,infrastructure,cloud",
            "experience_years": 10,
            "capacity": 15,
            "max_concurrent_tickets": 10,
            "role": "agent",
            "availability_status": "AVAILABLE",
            "timezone": "Asia/Kolkata",
            "shift_start": "08:00",
            "shift_end": "17:00",
            "work_days": "0,1,2,3,4",
            "auto_assignment_enabled": True,
        },
        {
            "name": "Meera Shah",
            "email": "meera@support.example.com",
            "password": "agent123",
            "team": "Finance Operations",
            "skills": "billing,invoice,payment,refund",
            "experience_years": 6,
            "capacity": 10,
            "max_concurrent_tickets": 7,
            "role": "agent",
            "availability_status": "AVAILABLE",
            "timezone": "Asia/Kolkata",
            "shift_start": "09:00",
            "shift_end": "18:00",
            "work_days": "0,1,2,3,4",
            "auto_assignment_enabled": True,
        },
        {
            "name": "Rohan Das",
            "email": "rohan@support.example.com",
            "password": "agent123",
            "team": "Fraud Investigation",
            "skills": "fraud,transaction,payment,investigation",
            "experience_years": 9,
            "capacity": 8,
            "max_concurrent_tickets": 5,
            "role": "agent",
            "availability_status": "AVAILABLE",
            "timezone": "Asia/Kolkata",
            "shift_start": "08:00",
            "shift_end": "17:00",
            "work_days": "0,1,2,3,4",
            "auto_assignment_enabled": True,
        },
        {
            "name": "Sara Iyer",
            "email": "sara@support.example.com",
            "password": "agent123",
            "team": "Cyber Security",
            "skills": "security,breach,account,identity",
            "experience_years": 8,
            "capacity": 7,
            "max_concurrent_tickets": 5,
            "role": "agent",
            "availability_status": "AVAILABLE",
            "timezone": "Asia/Kolkata",
            "shift_start": "11:00",
            "shift_end": "20:00",
            "work_days": "0,1,2,3,4",
            "auto_assignment_enabled": True,
        },
        {
            "name": "Vikram Rao",
            "email": "vikram@support.example.com",
            "password": "agent123",
            "team": "Site Reliability",
            "skills": "outage,incident,infrastructure,availability",
            "experience_years": 12,
            "capacity": 6,
            "max_concurrent_tickets": 4,
            "role": "agent",
            "availability_status": "AVAILABLE",
            "timezone": "Asia/Kolkata",
            "shift_start": "07:00",
            "shift_end": "16:00",
            "work_days": "0,1,2,3,4",
            "auto_assignment_enabled": True,
        },
    ]
    for data in agents:

        existing = (
            db.query(Agent)
            .filter(
                Agent.email == data["email"]
            )
            .first()
        )

        if existing:
            continue

        db.add(
            Agent(**data)
        )
    db.commit()
    print("Enterprise demo users, teams and agents created.")
finally:
    db.close()
