from app.database.db import SessionLocal
from app.models.user import User
from app.models.agent import Agent


db = SessionLocal()


# ============================================================
# USERS
# ============================================================

USERS = [
    {
        "name": "Admin",
        "email": "admin@complaints.com",
        "password": "password123",
        "role": "admin",
    },
    {
        "name": "Test Customer",
        "email": "customer@complaints.com",
        "password": "password123",
        "role": "user",
    },
]


# ============================================================
# RESOLVERS / AGENTS
# ============================================================

AGENTS = [
    {
        "name": "Alex Morgan",
        "email": "alex@support.com",
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
        "email": "priya@support.com",
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
        "email": "daniel@support.com",
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
        "email": "meera@support.com",
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
        "email": "rohan@support.com",
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
        "email": "sara@support.com",
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
        "email": "vikram@support.com",
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


def create_or_update_users():

    created = 0
    skipped = 0

    for data in USERS:

        existing = (
            db.query(User)
            .filter(
                User.email == data["email"]
            )
            .first()
        )

        if existing:
            print(
                f"[SKIP] User already exists: "
                f"{data['email']}"
            )

            skipped += 1
            continue

        user = User(**data)

        db.add(user)

        print(
            f"[ADD] User: "
            f"{data['email']}"
        )

        created += 1

    db.commit()

    return created, skipped


def create_or_update_agents():

    created = 0
    skipped = 0

    for data in AGENTS:

        existing = (
            db.query(Agent)
            .filter(
                Agent.email == data["email"]
            )
            .first()
        )

        if existing:
            print(
                f"[SKIP] Agent already exists: "
                f"{data['email']}"
            )

            skipped += 1
            continue

        agent = Agent(**data)

        db.add(agent)

        print(
            f"[ADD] Agent: "
            f"{data['name']} "
            f"({data['team']})"
        )

        created += 1

    db.commit()

    return created, skipped


try:

    print()
    print(
        "========================================"
    )
    print(
        "COMPLAINT ROUTING SEED"
    )
    print(
        "========================================"
    )

    print()
    print("Creating users...")

    user_created, user_skipped = (
        create_or_update_users()
    )

    print()
    print("Creating resolvers...")

    agent_created, agent_skipped = (
        create_or_update_agents()
    )

    print()
    print(
        "========================================"
    )
    print(
        "SEED COMPLETED"
    )
    print(
        "========================================"
    )

    print(
        f"Users   : "
        f"{user_created} created, "
        f"{user_skipped} already existed"
    )

    print(
        f"Agents  : "
        f"{agent_created} created, "
        f"{agent_skipped} already existed"
    )

finally:

    db.close()