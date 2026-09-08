from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from app.services.sla_service import SLAService
from sqlalchemy import func
from app.database.dependencies import get_db
from app.core.config import settings
from app.models.complaint import Complaint
from app.models.agent import Agent
from app.models.ticket_event import TicketEvent
from app.schemas.complaint_schema import StatusUpdate, PriorityUpdate, ManualAssignmentRequest
from app.services.assignment_service import AssignmentService
from app.services.priority_service import PriorityService
from app.services.workforce_service import WorkforceService
from app.services.business_calendar import (
    BusinessCalendar,
)
from app.schemas.ticket_schema import TicketAssignmentRequest
from app.schemas.ticket_schema import TicketEscalationRequest
from app.services.team_service import TeamService
from app.services.ticket_lifecycle_service import (
    TicketLifecycleService,
)
from app.services.sla_monitor_service import (
    SLAMonitorService,
)
from app.services.escalation_service import (
    EscalationService,
)
from app.services.ai_resolution_service import AIResolutionService
from app.services.similar_ticket_service import SimilarTicketService
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.notification_service import NotificationService

router = APIRouter(tags=["Tickets"])


@router.get("/tickets")
def get_tickets(status: str | None = None, team: str | None = None, priority: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Complaint)
    if status: query = query.filter(Complaint.status == status)
    if team: query = query.filter(Complaint.assigned_team == team)
    if priority: query = query.filter(Complaint.priority_level == priority)
    return query.order_by(Complaint.created_at.desc()).all()


@router.get("/tickets/customer/{customer_name}")
def get_customer_tickets(customer_name: str, db: Session = Depends(get_db)):
    return db.query(Complaint).filter(Complaint.customer_name == customer_name).order_by(Complaint.created_at.desc()).all()


@router.get("/tickets/agent/{agent_id}")
def get_agent_tickets(
    agent_id: int,
    db: Session = Depends(get_db),
):
    agent = (
        db.query(Agent)
        .filter(
            Agent.id == agent_id,
            Agent.active.is_(True),
        )
        .first()
    )

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found",
        )

    # ----------------------------------------------------------
    # IMPORTANT:
    # Return ALL tickets historically assigned to this resolver.
    #
    # We separate ACTIVE from HISTORICAL tickets so that:
    # - UI can show resolver history
    # - workforce/capacity still uses active tickets only
    # ----------------------------------------------------------

    tickets = (
        db.query(Complaint)
        .filter(
            Complaint.assigned_agent_id == agent_id,
        )
        .order_by(
            Complaint.created_at.desc()
        )
        .all()
    )

    active_statuses = {
        "OPEN",
        "IN_PROGRESS",
        "PENDING_CUSTOMER",
    }

    active_tickets = [
        ticket
        for ticket in tickets
        if ticket.status in active_statuses
    ]

    historical_tickets = [
        ticket
        for ticket in tickets
        if ticket.status in {
            "RESOLVED",
            "CLOSED",
        }
    ]

    # ----------------------------------------------------------
    # Enrich all tickets with SLA information.
    # ----------------------------------------------------------

    enriched = []

    for ticket in tickets:

        sla = SLAService.evaluate_resolution(
            priority_level=(
                ticket.priority_level
            ),
            deadline=(
                ticket.sla_deadline
            ),
            timezone_name="Asia/Kolkata",
        )

        enriched.append(
            {
                "ticket": ticket,

                "sla": sla,

                "sla_state": (
                    sla["state"]
                ),

                "remaining_seconds": (
                    sla["remaining_seconds"]
                ),

                "remaining_hours": (
                    sla["remaining_hours"]
                ),

                "sla_breached": (
                    sla["breached"]
                ),

                "sla_at_risk": (
                    sla["at_risk"]
                ),
            }
        )

    # ----------------------------------------------------------
    # Active tickets first.
    # Historical tickets afterward.
    # ----------------------------------------------------------

    priority_order = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    def sort_key(item):

        ticket = item["ticket"]

        is_active = (
            ticket.status in active_statuses
        )

        return (
            0 if is_active else 1,
            {
                "BREACHED": 0,
                "AT_RISK": 1,
                "ON_TRACK": 2,
                "NO_SLA": 3,
            }.get(
                item["sla_state"],
                4,
            ),
            -priority_order.get(
                ticket.priority_level,
                0,
            ),
            ticket.created_at,
        )

    enriched.sort(
        key=sort_key
    )

    # ----------------------------------------------------------
    # Workforce metrics MUST ONLY use active tickets.
    # ----------------------------------------------------------

    active_enriched = [
        item
        for item in enriched
        if item["ticket"].status
        in active_statuses
    ]

    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "team": agent.team,
            "experience_years": (
                agent.experience_years
            ),
            "skills": agent.skills,
            "availability_status": (
                agent.availability_status
            ),
            "on_call_enabled": (
                agent.on_call_enabled
            ),
            "shift_active": (
                WorkforceService.is_within_shift(
                    agent
                )
            ),
        },

        "summary": {
            # --------------------------------------------------
            # ACTIVE WORKLOAD
            # --------------------------------------------------

            "active_tickets": len(
                active_tickets
            ),

            "critical": sum(
                ticket.priority_level
                == "Critical"
                for ticket in active_tickets
            ),

            "high": sum(
                ticket.priority_level
                == "High"
                for ticket in active_tickets
            ),

            "sla_breached": sum(
                item["sla_breached"]
                for item in active_enriched
            ),

            "sla_at_risk": sum(
                item["sla_at_risk"]
                for item in active_enriched
            ),

            # --------------------------------------------------
            # HISTORICAL WORK
            # --------------------------------------------------

            "resolved_tickets": sum(
                ticket.status
                == "RESOLVED"
                for ticket in historical_tickets
            ),

            "closed_tickets": sum(
                ticket.status
                == "CLOSED"
                for ticket in historical_tickets
            ),

            "historical_tickets": len(
                historical_tickets
            ),

            "total_assigned_tickets": len(
                tickets
            ),

            # --------------------------------------------------
            # WORKFORCE
            # --------------------------------------------------

            "capacity": (
                agent.max_concurrent_tickets
                or agent.capacity
            ),

            "utilization": (
                len(active_tickets)
                / max(
                    agent.max_concurrent_tickets
                    or agent.capacity
                    or 1,
                    1,
                )
            ),
        },

        # ------------------------------------------------------
        # ALL assigned tickets
        # ------------------------------------------------------

        "tickets": [
            item["ticket"]
            for item in enriched
        ],

        # ------------------------------------------------------
        # Explicit subsets for frontend consumers
        # ------------------------------------------------------

        "active_tickets": [
            item["ticket"]
            for item in active_enriched
        ],

        "historical_tickets": [
            item["ticket"]
            for item in enriched
            if item["ticket"].status
            in {
                "RESOLVED",
                "CLOSED",
            }
        ],
    }

@router.put(
    "/tickets/{ticket_id}/status"
)
def update_ticket_status(
    ticket_id: int,
    request: StatusUpdate,
    db: Session = Depends(get_db),
):

    ticket = (
        db.query(Complaint)
        .filter(
            Complaint.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            404,
            "Ticket not found",
        )

    # An active work state requires an assigned resolver.
    # OPEN is the queue/assigned-but-not-started state.
    if request.status in {
        "IN_PROGRESS",
        "PENDING_CUSTOMER",
        "RESOLVED",
    } and ticket.assigned_agent_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ticket must be assigned to a resolver "
                f"before it can become {request.status}."
            ),
        )

    try:
        if (
            request.status == "PENDING_CUSTOMER"
            and ticket.first_response_at is None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Ticket cannot enter "
                    "PENDING_CUSTOMER before "
                    "the first response is recorded."
                ),
            )

        TicketLifecycleService.validate_transition(
            ticket.status,
            request.status,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    previous_status = (
        ticket.status
    )
    now = datetime.utcnow()
    # ---------------------------------------------
    # Pause resolution SLA
    # ---------------------------------------------

    if (
        request.status == "PENDING_CUSTOMER"
        and ticket.sla_paused_at is None
    ):

        ticket.sla_paused_at = now

    # ---------------------------------------------
    # Resume resolution SLA
    # ---------------------------------------------

    if (
        ticket.status == "PENDING_CUSTOMER"
        and request.status == "IN_PROGRESS"
        and ticket.sla_paused_at
    ):

        paused_seconds = (
            BusinessCalendar.business_seconds_between(
                ticket.sla_paused_at,
                now,
                "Asia/Kolkata",
            )
        )

        ticket.sla_total_paused_seconds = (
            (
                ticket.sla_total_paused_seconds
                or 0
            )
            + paused_seconds
        )

        if ticket.sla_deadline:

            ticket.sla_deadline = (
                BusinessCalendar.add_business_seconds(
                    start=ticket.sla_deadline,
                    seconds=paused_seconds,
                    timezone_name="Asia/Kolkata",
                )
            )

        ticket.sla_paused_at = None

    ticket.status = request.status

    # ---------------------------------------------
    # First response
    # ---------------------------------------------

    if (
        ticket.first_response_at is None
        and request.status
        in {
            "IN_PROGRESS",
            "RESOLVED",
        }
    ):

        ticket.first_response_at = now

    # ---------------------------------------------
    # Resolution
    # ---------------------------------------------

    if request.status == "RESOLVED":

        ticket.resolved_at = now

    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            event_type="STATUS_CHANGED",
            from_value=previous_status,
            to_value=request.status,
            notes=(
                f"Ticket status changed from {previous_status} "
                f"to {request.status}."
            ),
        )
    )

    NotificationService.status_change(
        db,
        ticket,
        previous_status,
        request.status,
    )

    db.commit()
    db.refresh(ticket)

    return {
        "ticket_id": ticket.id,
        "previous_status": (
            previous_status
        ),
        "status": ticket.status,
        "resolved_at": (
            ticket.resolved_at
        ),
    }

@router.put(
    "/tickets/{ticket_id}/priority"
)
def update_priority(
    ticket_id: int,
    request: PriorityUpdate,
    user_role: str | None = Header(
        default=None,
        alias="X-User-Role",
    ),
    db: Session = Depends(get_db),
):

    ticket = (
        db.query(Complaint)
        .filter(
            Complaint.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            404,
            "Ticket not found",
        )

    if ticket.status in {
        "CLOSED",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Closed tickets cannot "
                "have their priority changed."
            ),
        )

    if request.priority not in (
        PriorityService.LEVEL_SCORE
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid priority."
            ),
        )

    old_priority = (
        ticket.priority_level
    )

    ticket.priority_level = (
        request.priority
    )

    ticket.priority_score = (
        PriorityService.LEVEL_SCORE[
            request.priority
        ]
    )

    source_by_role = {
        "customer": "CUSTOMER",
        "agent": "AGENT",
        "admin": "ADMIN",
    }

    ticket.priority_source = (
        source_by_role.get(
            (user_role or "").lower(),
            "ADMIN",
        )
    )

    ticket.sla_hours = (
        PriorityService.SLA_HOURS[
            request.priority
        ]
    )

    ticket.sla_deadline = (
        SLAService.calculate_deadline(
            priority_level=(
                request.priority
            ),
            started_at=(
                ticket.created_at
                or datetime.utcnow()
            ),
            timezone_name="Asia/Kolkata",
        )
    )

    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            event_type="PRIORITY_CHANGED",
            from_value=old_priority,
            to_value=request.priority,
            notes=(
                f"Priority changed from {old_priority} "
                f"to {request.priority}. "
                f"Source={ticket.priority_source}."
            ),
        )
    )

    NotificationService.priority_change(
        db,
        ticket,
        old_priority,
        request.priority,
    )

    db.commit()
    db.refresh(ticket)

    return ticket

@router.put(
    "/tickets/{ticket_id}/assign"
)
def assign_ticket(
    ticket_id: int,
    request: TicketAssignmentRequest,
    db: Session = Depends(get_db),
):

    ticket = (
        db.query(Complaint)
        .filter(
            Complaint.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    # --------------------------------------------------
    # Lifecycle protection
    # --------------------------------------------------

    if ticket.status in {
        "CLOSED",
        "RESOLVED",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Resolved or closed tickets "
                "cannot be assigned."
            ),
        )

    # --------------------------------------------------
    # Agent validation
    # --------------------------------------------------

    agent = (
        db.query(Agent)
        .filter(
            Agent.id == request.agent_id,
            Agent.active.is_(True),
        )
        .first()
    )

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=(
                "Active resolver not found."
            ),
        )

    # --------------------------------------------------
    # Team validation
    # --------------------------------------------------

    # --------------------------------------------------
    # Resolve the ticket's operational team
    # --------------------------------------------------

    operational_team = TeamService.resolve_for_assignment(
        team=ticket.assigned_team,
        category=ticket.category,
        subcategory=ticket.subcategory,
    )

    # Keep the ticket aligned with the actual operational team.
    ticket.assigned_team = operational_team

    # --------------------------------------------------
    # Team validation
    # --------------------------------------------------

    if not TeamService.matches(
        agent.team,
        operational_team,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Resolver {agent.name} "
                f"belongs to '{agent.team}', "
                f"but ticket is routed to "
                f"'{operational_team}'."
            ),
        )

    # --------------------------------------------------
    # Workforce validation
    # --------------------------------------------------

    active_tickets = (
        db.query(Complaint)
        .filter(
            Complaint.assigned_agent_id
            == agent.id,
            Complaint.status.in_(
                [
                    "OPEN",
                    "IN_PROGRESS",
                    "PENDING_CUSTOMER",
                ]
            ),
        )
        .all()
    )

    workforce = (
        WorkforceService.evaluate(
            agent,
            len(active_tickets),
        )
    )

    # Manual assignment is allowed to BUSY agents,
    # but not to OFFLINE / ON_LEAVE / inactive agents.
    if agent.availability_status in {
        "OFFLINE",
        "ON_LEAVE",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Resolver {agent.name} "
                f"is currently "
                f"{agent.availability_status}."
            ),
        )

    max_capacity = (
        workforce[
            "max_concurrent_tickets"
        ]
    )

    manual_override_warning = None

    if len(active_tickets) >= max_capacity:
        manual_override_warning = (
            f"Manual assignment override: "
            f"{agent.name} is currently at capacity "
            f"({len(active_tickets)}/{max_capacity})."
        )

    # --------------------------------------------------
    # Assignment
    # --------------------------------------------------

    previous_agent_id = ticket.assigned_agent_id
    previous_agent_name = ticket.assigned_agent_name

    ticket.assigned_agent_id = agent.id

    ticket.assigned_agent_name = agent.name

    ticket.assignment_score = 100.0

    ticket.assignment_explanation = (
        "Manually assigned by operations "
        f"to {agent.name}."
    )

    if manual_override_warning:
        ticket.assignment_explanation += (
            f" {manual_override_warning}"
        )

    # Assignment and work-start are deliberately separate lifecycle events.
    # The ticket remains OPEN until the resolver explicitly starts work.
    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            event_type="MANUAL_ASSIGNED",
            from_value=(
                previous_agent_name
                or (
                    str(previous_agent_id)
                    if previous_agent_id
                    else None
                )
            ),
            to_value=agent.name,
            notes=(
                "Ticket manually assigned by operations. "
                f"Resolver={agent.name}. "
                + (
                    manual_override_warning
                    if manual_override_warning
                    else "Within normal resolver capacity."
                )
            ),
        )
    )

    NotificationService.assignment(
        db,
        ticket,
        agent_id=agent.id,
        agent_name=agent.name,
        mode="MANUAL",
        previous_agent_id=previous_agent_id,
    )

    db.commit()
    db.refresh(ticket)

    return ticket

@router.get("/tickets/{ticket_id}/events")
def ticket_events(ticket_id: int, db: Session = Depends(get_db)):
    return db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.created_at.desc()).all()



@router.post(
    "/tickets/{ticket_id}/ai-resolution-recommendation"
)
def ai_resolution_recommendation(
    ticket_id: int,
    db: Session = Depends(get_db),
):
    """Generate resolver-facing troubleshooting guidance for an active ticket."""
    ticket = (
        db.query(Complaint)
        .filter(Complaint.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if ticket.status in {"CLOSED", "RESOLVED"}:
        raise HTTPException(
            409,
            "Resolution guidance is intended for active tickets.",
        )

    try:
        context = HybridRetrievalService.resolution_context(
            ticket,
            db,
            ticket_limit=4,
            sop_limit=2,
            kb_limit=3,
        )
        recommendation = AIResolutionService.recommend(
            ticket,
            context,
        )
    except Exception as exc:
        raise HTTPException(
            502,
            detail=f"AI resolution recommendation failed: {exc}",
        )

    return {
        "ticket_id": ticket.id,
        "generated_by": "Groq",
        "model": settings.MODEL_NAME,
        "retrieval": {
            "method": context["method"],
            "embedding_model": context["embedding_model"],
            "reranker_model": context["reranker_model"],
        },
        "recommendation": recommendation,
        "context": context,
    }


@router.get(
    "/tickets/{ticket_id}/similar-resolved"
)
def similar_resolved_tickets(
    ticket_id: int,
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Return previously resolved/closed tickets similar to the current ticket."""
    ticket = (
        db.query(Complaint)
        .filter(Complaint.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    resolved_tickets = (
        db.query(Complaint)
        .filter(
            Complaint.id != ticket.id,
            Complaint.status.in_(["RESOLVED", "CLOSED"]),
        )
        .order_by(Complaint.resolved_at.desc(), Complaint.created_at.desc())
        .limit(250)
        .all()
    )

    context = HybridRetrievalService.resolution_context(
        ticket,
        db,
        ticket_limit=limit,
        sop_limit=0,
        kb_limit=0,
    )

    results = []
    for item in context["tickets"]:
        results.append(
            {
                "ticket_id": item["ticket_id"],
                "similarity_score": round(
                    float(item.get("rerank_score_normalized", 0.0)),
                    3,
                ),
                "category": item.get("category"),
                "subcategory": item.get("subcategory"),
                "priority_level": item.get("priority_level"),
                "summary": item.get("summary"),
                "complaint_text": item.get("complaint_text"),
                "resolved_at": item.get("resolved_at"),
                "assigned_agent_name": item.get("assigned_agent_name"),
                "resolution_outcome": item.get("content"),
                "status": item.get("status"),
                "dense_score": item.get("dense_score"),
                "sparse_score": item.get("sparse_score"),
                "rerank_score": item.get("rerank_score"),
                "rerank_score_normalized": item.get("rerank_score_normalized"),
            }
        )

    return {
        "ticket_id": ticket.id,
        "count": len(results),
        "retrieval_method": context["method"],
        "tickets": results,
    }


@router.get(
    "/tickets/{ticket_id}/resolution-context"
)
def resolution_context(
    ticket_id: int,
    db: Session = Depends(get_db),
):
    """Return the resolver-facing evidence retrieved from tickets, SOP and KB."""
    ticket = (
        db.query(Complaint)
        .filter(Complaint.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    try:
        context = HybridRetrievalService.resolution_context(
            ticket,
            db,
            ticket_limit=4,
            sop_limit=2,
            kb_limit=3,
        )
    except Exception as exc:
        raise HTTPException(
            502,
            detail=f"Resolution context retrieval failed: {exc}",
        )

    return {
        "ticket_id": ticket.id,
        **context,
    }


@router.get("/tickets/dashboard")
def dashboard(
    db: Session = Depends(get_db),
):
    tickets = (
        db.query(Complaint)
        .order_by(
            Complaint.created_at.desc()
        )
        .all()
    )

    now = datetime.utcnow()

    active_tickets = [
        ticket
        for ticket in tickets
        if ticket.status
        not in {
            "RESOLVED",
            "CLOSED",
        }
    ]

    # --------------------------------------------------
    # SLA
    # --------------------------------------------------

    sla_states = {}

    for ticket in active_tickets:

        sla_states[ticket.id] = (
            SLAService.evaluate_resolution(
                priority_level=(
                    ticket.priority_level
                ),
                deadline=(
                    ticket.sla_deadline
                ),
                timezone_name="Asia/Kolkata",
            )
        )

    breached = [
        ticket
        for ticket in active_tickets
        if sla_states[
            ticket.id
        ]["breached"]
    ]

    at_risk = [
        ticket
        for ticket in active_tickets
        if sla_states[
            ticket.id
        ]["at_risk"]
        and not sla_states[
            ticket.id
        ]["breached"]
    ]

    # --------------------------------------------------
    # Queue
    # --------------------------------------------------

    unassigned = [
        ticket
        for ticket in active_tickets
        if ticket.assigned_agent_id is None
    ]

    # --------------------------------------------------
    # Escalation metrics
    # --------------------------------------------------

    escalated_tickets = [
        ticket
        for ticket in active_tickets
        if ticket.escalation_required
    ]

    escalation_levels = {
        "level_1": sum(
            (
                ticket.escalation_level
                or 0
            ) == 1
            for ticket in escalated_tickets
        ),

        "level_2": sum(
            (
                ticket.escalation_level
                or 0
            ) == 2
            for ticket in escalated_tickets
        ),

        "level_3": sum(
            (
                ticket.escalation_level
                or 0
            ) >= 3
            for ticket in escalated_tickets
        ),
    }

    # --------------------------------------------------
    # Workforce
    # --------------------------------------------------

    agents = (
        db.query(Agent)
        .filter(
            Agent.active.is_(True)
        )
        .order_by(
            Agent.team,
            Agent.name,
        )
        .all()
    )

    workforce = []

    for agent in agents:

        agent_tickets = (
            db.query(Complaint)
            .filter(
                Complaint.assigned_agent_id
                == agent.id,

                Complaint.status.in_(
                    [
                        "OPEN",
                        "IN_PROGRESS",
                        "PENDING_CUSTOMER",
                    ]
                ),
            )
            .all()
        )

        workforce_state = (
            WorkforceService.evaluate(
                agent,
                len(agent_tickets),
            )
        )

        effective_workload = (
            AssignmentService._calculate_workload(
                agent_tickets
            )
        )

        critical_count = sum(
            ticket.priority_level
            == "Critical"
            for ticket in agent_tickets
        )

        high_count = sum(
            ticket.priority_level
            == "High"
            for ticket in agent_tickets
        )

        agent_breaches = sum(
            sla_states.get(
                ticket.id,
                {},
            ).get(
                "breached",
                False,
            )
            for ticket in agent_tickets
        )

        agent_at_risk = sum(
            (
                sla_states.get(
                    ticket.id,
                    {},
                ).get(
                    "at_risk",
                    False,
                )
                and not sla_states.get(
                    ticket.id,
                    {},
                ).get(
                    "breached",
                    False,
                )
            )
            for ticket in agent_tickets
        )

        workforce.append(
            {
                "id": agent.id,

                "name": agent.name,

                "email": agent.email,

                "team": agent.team,

                "skills": agent.skills,

                "experience_years": (
                    agent.experience_years
                ),

                "status": (
                    agent.availability_status
                ),

                "shift_active": (
                    workforce_state[
                        "shift_active"
                    ]
                ),

                "shift_start": (
                    agent.shift_start
                ),

                "shift_end": (
                    agent.shift_end
                ),

                "timezone": (
                    agent.timezone
                ),

                "open_tickets": len(
                    agent_tickets
                ),

                "effective_workload": round(
                    effective_workload,
                    2,
                ),

                "capacity": (
                    workforce_state[
                        "max_concurrent_tickets"
                    ]
                ),

                "utilization": (
                    workforce_state[
                        "utilization"
                    ]
                ),

                "capacity_available": (
                    workforce_state[
                        "capacity_available"
                    ]
                ),

                "eligible_for_assignment": (
                    workforce_state[
                        "eligible"
                    ]
                ),

                "auto_assignment_enabled": (
                    agent.auto_assignment_enabled
                ),

                "on_call_enabled": (
                    agent.on_call_enabled
                ),

                "critical_tickets": (
                    critical_count
                ),

                "high_tickets": (
                    high_count
                ),

                "sla_breaches": (
                    int(agent_breaches)
                ),

                "sla_at_risk": (
                    int(agent_at_risk)
                ),

                "workforce_reasons": (
                    workforce_state[
                        "reasons"
                    ]
                ),
            }
        )

    # --------------------------------------------------
    # Team metrics
    # --------------------------------------------------

    teams = {}

    for agent in workforce:

        team_name = agent["team"]

        if team_name not in teams:

            teams[team_name] = {
                "team": team_name,
                "agents": 0,
                "available_agents": 0,
                "eligible_agents": 0,
                "tickets": 0,
                "effective_workload": 0,
                "critical_tickets": 0,
                "sla_breaches": 0,
            }

        team = teams[team_name]

        team["agents"] += 1

        if agent["status"] == "AVAILABLE":
            team["available_agents"] += 1

        if agent[
            "eligible_for_assignment"
        ]:
            team["eligible_agents"] += 1

        team["tickets"] += agent[
            "open_tickets"
        ]

        team["effective_workload"] += (
            agent[
                "effective_workload"
            ]
        )

        team["critical_tickets"] += (
            agent[
                "critical_tickets"
            ]
        )

        team["sla_breaches"] += (
            agent[
                "sla_breaches"
            ]
        )

    for team in teams.values():

        team[
            "effective_workload"
        ] = round(
            team[
                "effective_workload"
            ],
            2,
        )

    # --------------------------------------------------
    # Final dashboard
    # --------------------------------------------------

    return {
        "generated_at": now.isoformat(),

        "total": len(tickets),

        "open": sum(
            ticket.status == "OPEN"
            for ticket in tickets
        ),

        "in_progress": sum(
            ticket.status
            == "IN_PROGRESS"
            for ticket in tickets
        ),

        "pending_customer": sum(
            ticket.status
            == "PENDING_CUSTOMER"
            for ticket in tickets
        ),

        "resolved": sum(
            ticket.status
            in {
                "RESOLVED",
                "CLOSED",
            }
            for ticket in tickets
        ),

        "critical": sum(
            ticket.priority_level
            == "Critical"
            for ticket in active_tickets
        ),

        "high": sum(
            ticket.priority_level
            == "High"
            for ticket in active_tickets
        ),

        "sla_breached": len(
            breached
        ),

        "sla_at_risk": len(
            at_risk
        ),

        "unassigned": len(
            unassigned
        ),

        # ----------------------------------------------
        # Escalation data belongs at dashboard root
        # ----------------------------------------------

        "escalated": len(
            escalated_tickets
        ),

        "escalation_levels": (
            escalation_levels
        ),

        "workforce": workforce,

        "teams": list(
            teams.values()
        ),

        "workforce_summary": {
            "total_agents": len(
                agents
            ),

            "available": sum(
                agent["status"]
                == "AVAILABLE"
                for agent in workforce
            ),

            "busy": sum(
                agent["status"]
                == "BUSY"
                for agent in workforce
            ),

            "away": sum(
                agent["status"]
                == "AWAY"
                for agent in workforce
            ),

            "offline": sum(
                agent["status"]
                == "OFFLINE"
                for agent in workforce
            ),

            "on_leave": sum(
                agent["status"]
                == "ON_LEAVE"
                for agent in workforce
            ),

            "eligible": sum(
                agent[
                    "eligible_for_assignment"
                ]
                for agent in workforce
            ),

            "at_capacity": sum(
                not agent[
                    "capacity_available"
                ]
                for agent in workforce
            ),
        },
    }


@router.get(
    "/tickets/{ticket_id}/assignment-analysis"
)
def assignment_analysis(
    ticket_id: int,
    db: Session = Depends(get_db),
):

    ticket = (
        db.query(Complaint)
        .filter(
            Complaint.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            404,
            "Ticket not found",
        )

    analysis = (
        AssignmentService.choose_agent(
            db=db,
            team=ticket.assigned_team,
            category=ticket.category,
            subcategory=ticket.subcategory,
            priority_level=ticket.priority_level,
        )
    )

    if not analysis:
        return {
            "ticket_id": ticket.id,

            "ticket": {
                "category": ticket.category,
                "subcategory": ticket.subcategory,
                "priority": ticket.priority_level,
                "assigned_team": (
                    ticket.assigned_team
                ),
            },

            "selected": None,

            "candidate_count": 0,

            "candidates": [],

            "message": (
                "No resolver is currently "
                "eligible for this ticket."
            ),
        }

    return {
        "ticket_id": ticket.id,

        "ticket": {
            "category": ticket.category,
            "subcategory": ticket.subcategory,
            "priority": ticket.priority_level,
            "assigned_team": (
                ticket.assigned_team
            ),
        },

        "selected": {
            "agent_id": (
                analysis["agent"].id
            ),
            "agent_name": (
                analysis["agent"].name
            ),
            "score": analysis["score"],
            "explanation": (
                analysis["explanation"]
            ),
        },

        "candidate_count": (
            analysis["candidate_count"]
        ),

        "candidates": (
            analysis["candidate_breakdown"]
        ),
    }

@router.get(
    "/tickets/{ticket_id}/sla"
)
def get_ticket_sla(
    ticket_id: int,
    db: Session = Depends(get_db),
):

    ticket = (
        db.query(Complaint)
        .filter(
            Complaint.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            404,
            "Ticket not found",
        )

    result = (
        SLAMonitorService.evaluate_ticket(
            ticket
        )
    )

    return {
        "ticket_id": ticket.id,

        "ticket": {
            "id": ticket.id,
            "priority": ticket.priority_level,
            "status": ticket.status,
            "assigned_agent_id": (
                ticket.assigned_agent_id
            ),
            "assigned_agent_name": (
                ticket.assigned_agent_name
            ),
        },

        "first_response": (
            result["first_response"]
        ),

        "resolution": (
            result["resolution"]
        ),

        "escalation": (
            result["escalation"]
        ),

        "pause": {
            "paused": (
                ticket.sla_paused_at
                is not None
            ),

            "paused_at": (
                ticket.sla_paused_at
            ),

            "total_paused_seconds": (
                ticket.sla_total_paused_seconds
                or 0
            ),
        },
    }

@router.post(
    "/tickets/{ticket_id}/auto-assign"
)
def auto_assign_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
):
    ticket = (
        db.query(Complaint)
        .filter(
            Complaint.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    if ticket.status in (
        "RESOLVED",
        "CLOSED",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Resolved or closed tickets "
                "cannot be auto-assigned."
            ),
        )

    result = AssignmentService.choose_agent(
        db=db,
        team=ticket.assigned_team,
        category=ticket.category,
        subcategory=ticket.subcategory,
        priority_level=ticket.priority_level,
    )

    if not result:
        return {
            "success": False,
            "ticket_id": ticket.id,
            "message": (
                "No eligible resolver is "
                "currently available."
            ),
        }

    agent = result["agent"]

    operational_team = TeamService.resolve_for_assignment(
        team=ticket.assigned_team,
        category=ticket.category,
        subcategory=ticket.subcategory,
    )

    ticket.assigned_team = operational_team

    ticket.assigned_agent_id = agent.id
    ticket.assigned_agent_name = agent.name
    ticket.assignment_score = result["score"]
    ticket.assignment_explanation = (
        result["explanation"]
    )

    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            event_type="AUTO_ASSIGNED",
            from_value=None,
            to_value=agent.name,
            notes=result["explanation"],
        )
    )

    NotificationService.assignment(
        db,
        ticket,
        agent_id=agent.id,
        agent_name=agent.name,
        mode="AUTO",
        previous_agent_id=None,
    )

    # Assignment does not mean the resolver has started work.
    # The ticket remains OPEN until the resolver changes it to IN_PROGRESS.
    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "ticket_id": ticket.id,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "score": result["score"],
        "explanation": result["explanation"],
    }

@router.post(
    "/tickets/auto-assign-unassigned"
)
def auto_assign_unassigned(
    db: Session = Depends(get_db),
):
    tickets = (
        db.query(Complaint)
        .filter(
            Complaint.assigned_agent_id.is_(None),
            Complaint.status.notin_(
                [
                    "RESOLVED",
                    "CLOSED",
                ]
            ),
        )
        .order_by(
            Complaint.priority_score.desc(),
            Complaint.created_at.asc(),
        )
        .all()
    )

    results = []

    assigned = 0
    skipped = 0

    for ticket in tickets:

        result = AssignmentService.choose_agent(
            db=db,
            team=ticket.assigned_team,
            category=ticket.category,
            subcategory=ticket.subcategory,
            priority_level=ticket.priority_level,
        )

        if not result:
            operational_team = TeamService.resolve_for_assignment(
                team=ticket.assigned_team,
                category=ticket.category,
                subcategory=ticket.subcategory,
            )

            team_agents = (
                db.query(Agent)
                .filter(
                    Agent.active.is_(True)
                )
                .all()
            )

            matching_agents = [
                agent
                for agent in team_agents
                if TeamService.matches(
                    agent.team,
                    operational_team,
                )
            ]

            if not matching_agents:
                reason = (
                    f"No active resolver exists in "
                    f"operational team '{operational_team}'. "
                    f"Original team='{ticket.assigned_team}'."
                )
            else:
                reason = (
                    f"Resolvers exist in '{operational_team}', "
                    f"but none currently satisfy workforce, "
                    f"capacity, skill or availability rules."
                )

            skipped += 1

            results.append(
                {
                    "ticket_id": ticket.id,
                    "status": "SKIPPED",
                    "original_team": ticket.assigned_team,
                    "resolved_team": operational_team,
                    "reason": reason,
                }
            )

            continue


        agent = result["agent"]
        operational_team = TeamService.resolve_for_assignment(
            team=ticket.assigned_team,
            category=ticket.category,
            subcategory=ticket.subcategory,
        )

        ticket.assigned_team = operational_team

        ticket.assigned_agent_id = agent.id
        ticket.assigned_agent_name = (
            agent.name
        )

        ticket.assignment_score = (
            result["score"]
        )

        ticket.assignment_explanation = (
            result["explanation"]
        )

        db.add(
            TicketEvent(
                ticket_id=ticket.id,
                event_type="AUTO_ASSIGNED",
                from_value=None,
                to_value=agent.name,
                notes=result["explanation"],
            )
        )

        NotificationService.assignment(
            db,
            ticket,
            agent_id=agent.id,
            agent_name=agent.name,
            mode="AUTO",
            previous_agent_id=None,
        )

        # Keep OPEN until the resolver starts work.
        assigned += 1

        results.append(
            {
                "ticket_id": ticket.id,
                "status": "ASSIGNED",
                "agent_id": agent.id,
                "agent_name": agent.name,
                "score": result["score"],
                "explanation": (
                    result["explanation"]
                ),
            }
        )

        # Commit after each assignment so that the
        # next candidate calculation sees the updated
        # workload.
        db.commit()

    return {
        "total_unassigned": len(tickets),
        "assigned": assigned,
        "skipped": skipped,
        "results": results,
    }

@router.post(
    "/tickets/{ticket_id}/escalate"
)
def escalate_ticket(
    ticket_id: int,
    request: TicketEscalationRequest,
    db: Session = Depends(get_db),
):

    ticket = (
        db.query(Complaint)
        .filter(
            Complaint.id == ticket_id
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            404,
            "Ticket not found",
        )

    if ticket.status in {
        "CLOSED",
    }:
        raise HTTPException(
            409,
            "Closed tickets cannot be escalated.",
        )

    previous_level = (
        ticket.escalation_level
        or 0
    )

    ticket.escalation_level = min(
        previous_level + 1,
        3,
    )

    ticket.escalated_at = (
        datetime.utcnow()
    )

    ticket.escalation_reason = (
        request.reason
    )

    ticket.escalation_owner = (
        request.target
        or EscalationService.determine_owner(
            ticket,
            ticket.escalation_level,
        )
    )

    ticket.escalation_count = (
        (ticket.escalation_count or 0)
        + 1
    )

    ticket.escalation_required = True

    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            event_type="MANUAL_ESCALATION",
            from_value=str(
                previous_level
            ),
            to_value=str(
                ticket.escalation_level
            ),
        )
    )

    db.commit()
    db.refresh(ticket)

    return {
        "ticket_id": ticket.id,
        "escalation_level": (
            ticket.escalation_level
        ),
        "owner": (
            ticket.escalation_owner
        ),
        "reason": (
            ticket.escalation_reason
        ),
    }

@router.post(
    "/tickets/run-sla-monitor"
)
def run_sla_monitor(
    db: Session = Depends(get_db),
):

    tickets = (
        db.query(Complaint)
        .filter(
            Complaint.status.notin_(
                [
                    "CLOSED",
                ]
            )
        )
        .all()
    )

    evaluated = 0
    escalated = 0

    results = []

    for ticket in tickets:

        result = (
            SLAMonitorService.apply_ticket(
                ticket,
                db,
            )
        )

        evaluated += 1

        if result["escalation"][
            "should_escalate"
        ]:

            escalated += 1

        results.append(
            {
                "ticket_id": ticket.id,
                "first_response": (
                    result[
                        "first_response"
                    ]["state"]
                ),
                "resolution": (
                    result[
                        "resolution"
                    ]["state"]
                ),
                "escalation": (
                    result[
                        "escalation"
                    ]
                ),
            }
        )

    return {
        "evaluated": evaluated,
        "escalated": escalated,
        "results": results,
    }
@router.post("/tickets/{ticket_id}/launch-cost-center-eib")
def launch_cost_center_eib(
    ticket_id: int,
    x_user_id: str | None = Header(None),
    x_user_role: str | None = Header(None),
    db: Session = Depends(get_db),
):
    from app.models.ticket_attachment import TicketAttachment
    from app.services.workday_eib_service import WorkdayEIBService

    print(f"[EIB DEBUG 01] Launch endpoint entered | ticket_id={ticket_id}", flush=True)
    print(f"[EIB DEBUG 02] Request headers received | user_id={x_user_id} | role={x_user_role}", flush=True)

    ticket = db.query(Complaint).filter(Complaint.id == ticket_id).first()
    print(f"[EIB DEBUG 03] Ticket lookup complete | found={ticket is not None}", flush=True)
    if not ticket:
        print("[EIB DEBUG ERROR] Ticket not found", flush=True)
        raise HTTPException(404, "Ticket not found")

    print(
        f"[EIB DEBUG 04] Ticket details | request_type={ticket.request_type} | "
        f"assigned_agent_id={ticket.assigned_agent_id} | status={getattr(ticket, 'status', None)}",
        flush=True,
    )

    if ticket.request_type != "WORKDAY_COST_CENTER_EIB":
        print("[EIB DEBUG ERROR] Ticket is not a Cost Center EIB request", flush=True)
        raise HTTPException(400, "This ticket is not a Cost Center EIB request.")
    print("[EIB DEBUG 05] Cost Center EIB workflow check passed", flush=True)

    try:
        current_user_id = int(x_user_id or 0)
    except ValueError:
        current_user_id = 0
    print(f"[EIB DEBUG 06] Current user parsed | current_user_id={current_user_id}", flush=True)

    if current_user_id != ticket.assigned_agent_id or (x_user_role or "").lower() != "agent":
        print("[EIB DEBUG ERROR] Resolver authorization failed", flush=True)
        raise HTTPException(403, "Only the assigned resolver can launch this EIB.")
    print("[EIB DEBUG 07] Resolver authorization passed", flush=True)

    print(
        f"[EIB DEBUG 08] Configured EIB resolver check | configured_agent_id={settings.WD_COST_CENTER_AGENT_ID}",
        flush=True,
    )
    if ticket.assigned_agent_id != settings.WD_COST_CENTER_AGENT_ID:
        print("[EIB DEBUG ERROR] Ticket is not assigned to configured EIB resolver", flush=True)
        raise HTTPException(403, "This EIB workflow is restricted to the configured resolver.")
    print("[EIB DEBUG 09] Configured resolver check passed", flush=True)

    print("[EIB DEBUG 10] Looking up ticket attachment", flush=True)
    attachment = (
        db.query(TicketAttachment)
        .filter(TicketAttachment.ticket_id == ticket_id)
        .first()
    )
    print(f"[EIB DEBUG 11] Attachment lookup complete | found={attachment is not None}", flush=True)
    if not attachment:
        print("[EIB DEBUG ERROR] No EIB attachment found", flush=True)
        raise HTTPException(400, "No EIB attachment is available for this ticket.")

    print(
        f"[EIB DEBUG 12] Attachment loaded | filename={attachment.filename} | "
        f"content_type={attachment.content_type} | size_bytes={len(attachment.content or b'')}",
        flush=True,
    )
    print("[EIB DEBUG 13] Starting Workday EIB launch service", flush=True)

    try:
        result = WorkdayEIBService.launch(
            file_content=attachment.content,
            filename=attachment.filename,
            content_type=attachment.content_type,
            endpoint=settings.WD_DEFAULT_ENDPOINT,
            username=settings.WD_DEFAULT_USERNAME,
            password=settings.WD_DEFAULT_PASSWORD,
            integration_system_id=settings.WD_COST_CENTER_INTEGRATION_ID,
        )
        print(
            f"[EIB DEBUG 14] Workday EIB service returned | status={result.get('status')} | "
            f"status_code={result.get('status_code')}",
            flush=True,
        )
    except Exception as exc:
        print(
            f"[EIB DEBUG ERROR] Workday EIB launch failed | type={type(exc).__name__} | error={exc}",
            flush=True,
        )
        raise HTTPException(502, detail=str(exc))

    print("[EIB DEBUG 15] Creating audit event", flush=True)
    db.add(TicketEvent(
        ticket_id=ticket.id,
        event_type="WORKDAY_EIB_LAUNCHED",
        to_value=attachment.filename,
        notes="Cost Center EIB launch request submitted to Workday.",
    ))
    print("[EIB DEBUG 16] Committing audit event to database", flush=True)
    db.commit()
    print("[EIB DEBUG 17] Database commit complete", flush=True)

    print(f"[EIB DEBUG 18] Launch endpoint completed successfully | ticket_id={ticket_id}", flush=True)
    return {
        "ticket_id": ticket.id,
        "status": "SUCCESS",
        "message": result["message"],
        "filename": attachment.filename,
    }
