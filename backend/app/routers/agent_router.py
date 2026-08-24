from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.agent import Agent
from app.models.complaint import Complaint
from app.schemas.agent_schema import (
    AgentCapacityUpdate,
    AgentCreate,
    AgentScheduleUpdate,
    AgentStatusUpdate,
    AgentOnCallUpdate,
)
from app.services.workforce_service import (
    WorkforceService,
)


router = APIRouter(
    tags=["Agents"]
)


ACTIVE_STATUSES = [
    "OPEN",
    "IN_PROGRESS",
    "PENDING_CUSTOMER",
]


@router.get("/agents")
def agents(
    db: Session = Depends(get_db),
):

    rows = (
        db.query(Agent)
        .filter(Agent.active.is_(True))
        .all()
    )

    result = []

    for agent in rows:

        open_tickets = (
            db.query(
                func.count(
                    Complaint.id
                )
            )
            .filter(
                Complaint.assigned_agent_id
                == agent.id,
                Complaint.status.in_(
                    ACTIVE_STATUSES
                ),
            )
            .scalar()
            or 0
        )

        workforce = (
            WorkforceService.evaluate(
                agent,
                open_tickets,
            )
        )

        result.append(
            {
                "id": agent.id,
                "name": agent.name,
                "email": agent.email,
                "team": agent.team,
                "role": agent.role,
                "skills": agent.skills,
                "experience_years": (
                    agent.experience_years
                ),
                "capacity": agent.capacity,
                "max_concurrent_tickets": (
                    workforce[
                        "max_concurrent_tickets"
                    ]
                ),
                "active": agent.active,

                "open_tickets": open_tickets,

                "utilization": workforce[
                    "utilization"
                ],

                "availability_status": (
                    workforce[
                        "availability_status"
                    ]
                ),

                "shift_active": workforce[
                    "shift_active"
                ],

                "capacity_available": workforce[
                    "capacity_available"
                ],

                "auto_assignment_enabled": (
                    agent.auto_assignment_enabled
                ),

                "timezone": agent.timezone,

                "shift_start": (
                    agent.shift_start
                ),

                "shift_end": (
                    agent.shift_end
                ),

                "work_days": (
                    agent.work_days
                ),

                "eligible_for_assignment": (
                    workforce["eligible"]
                ),

                "workforce_reasons": (
                    workforce["reasons"]
                ),
                "on_call_enabled": (
                    agent.on_call_enabled
                ),
            }
        )

    return result


@router.post("/agents")
def create_agent(
    request: AgentCreate,
    db: Session = Depends(get_db),
):

    existing = (
        db.query(Agent)
        .filter(
            Agent.email == request.email
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Agent email already exists",
        )

    payload = request.model_dump()

    if (
        payload["max_concurrent_tickets"]
        is None
    ):
        payload[
            "max_concurrent_tickets"
        ] = payload["capacity"]

    agent = Agent(**payload)

    db.add(agent)
    db.commit()
    db.refresh(agent)

    return agent


@router.put("/agents/{agent_id}/status")
def update_agent_status(
    agent_id: int,
    request: AgentStatusUpdate,
    db: Session = Depends(get_db),
):

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not agent:
        raise HTTPException(
            404,
            "Agent not found",
        )

    valid_statuses = (
        WorkforceService.VALID_STATUSES
    )

    if (
        request.availability_status
        not in valid_statuses
    ):
        raise HTTPException(
            400,
            (
                "Invalid availability status. "
                f"Allowed: "
                f"{', '.join(sorted(valid_statuses))}"
            ),
        )

    agent.availability_status = (
        request.availability_status
    )

    from datetime import datetime

    agent.last_status_change_at = (
        datetime.utcnow()
    )

    db.commit()
    db.refresh(agent)

    return agent


@router.put(
    "/agents/{agent_id}/capacity"
)
def update_agent_capacity(
    agent_id: int,
    request: AgentCapacityUpdate,
    db: Session = Depends(get_db),
):

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not agent:
        raise HTTPException(
            404,
            "Agent not found",
        )

    agent.max_concurrent_tickets = (
        request.max_concurrent_tickets
    )

    db.commit()
    db.refresh(agent)

    return agent


@router.put(
    "/agents/{agent_id}/schedule"
)
def update_agent_schedule(
    agent_id: int,
    request: AgentScheduleUpdate,
    db: Session = Depends(get_db),
):

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not agent:
        raise HTTPException(
            404,
            "Agent not found",
        )

    agent.timezone = request.timezone
    agent.shift_start = (
        request.shift_start
    )
    agent.shift_end = (
        request.shift_end
    )
    agent.work_days = (
        request.work_days
    )

    db.commit()
    db.refresh(agent)

    return agent


@router.get(
    "/agents/{agent_id}/workforce"
)
def agent_workforce(
    agent_id: int,
    db: Session = Depends(get_db),
):

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not agent:
        raise HTTPException(
            404,
            "Agent not found",
        )

    count = (
        db.query(
            func.count(Complaint.id)
        )
        .filter(
            Complaint.assigned_agent_id
            == agent.id,
            Complaint.status.in_(
                ACTIVE_STATUSES
            ),
        )
        .scalar()
        or 0
    )

    return WorkforceService.evaluate(
        agent,
        count,
    )

@router.get(
    "/agents/{agent_id}/workforce/debug"
)
def workforce_debug(
    agent_id: int,
    db: Session = Depends(get_db),
):
    agent = (
        db.query(Agent)
        .filter(
            Agent.id == agent_id
        )
        .first()
    )

    if not agent:
        raise HTTPException(
            404,
            "Agent not found",
        )

    active_ticket_count = (
        db.query(
            func.count(Complaint.id)
        )
        .filter(
            Complaint.assigned_agent_id
            == agent.id,
            Complaint.status.in_(
                ACTIVE_STATUSES
            ),
        )
        .scalar()
        or 0
    )

    state = WorkforceService.evaluate(
        agent,
        active_ticket_count,
    )

    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "timezone": agent.timezone,
            "shift_start": agent.shift_start,
            "shift_end": agent.shift_end,
            "work_days": agent.work_days,
            "status": agent.availability_status,
        },

        "server_utc": (
            datetime.utcnow().isoformat()
        ),

        "workforce": state,
    }

@router.put(
    "/agents/{agent_id}/on-call"
)
def update_agent_on_call(
    agent_id: int,
    request: AgentOnCallUpdate,
    db: Session = Depends(get_db),
):

    agent = (
        db.query(Agent)
        .filter(
            Agent.id == agent_id
        )
        .first()
    )

    if not agent:
        raise HTTPException(
            404,
            "Agent not found",
        )

    agent.on_call_enabled = (
        request.on_call_enabled
    )

    db.commit()
    db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "on_call_enabled": (
            agent.on_call_enabled
        ),
    }