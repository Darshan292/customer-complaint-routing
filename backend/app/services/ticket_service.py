import json
from datetime import datetime
from app.models.complaint import Complaint
from app.models.ticket_event import TicketEvent
# from datetime import datetime

from app.services.team_service import TeamService

from app.services.sla_service import SLAService


class TicketService:
    @staticmethod
    def create_ticket(db, request, analysis, assignment):
        priority_level = analysis.priority_level

        sla_hours = SLAService.get_sla_hours(
            priority_level
        )

        created_at = datetime.utcnow()

        sla_hours = SLAService.get_sla_hours(
            priority_level
        )

        first_response_minutes = (
            SLAService.get_first_response_minutes(
                priority_level
            )
        )

        sla_deadline = (
            SLAService.calculate_deadline(
                priority_level=priority_level,
                started_at=created_at,
                timezone_name="Asia/Kolkata",
            )
        )

        first_response_deadline = (
            SLAService.calculate_first_response_deadline(
                priority_level=priority_level,
                started_at=created_at,
                timezone_name="Asia/Kolkata",
            )
        )
        assigned_team = TeamService.canonicalize(
            analysis.assigned_team
        )
        ticket = Complaint(
            customer_name=request.customer_name,
            customer_tier=request.customer_tier,
            complaint_text=request.complaint_text,
            category=analysis.category,
            subcategory=analysis.subcategory,
            sentiment=analysis.sentiment,
            emotion=analysis.emotion,
            business_impact=analysis.business_impact,
            customer_intent=analysis.customer_intent,
            summary=analysis.summary,
            confidence=analysis.confidence,
            keywords=json.dumps(analysis.keywords),
            priority_score=analysis.priority_score,
            priority_level=analysis.priority_level,
            priority_source=analysis.priority_source,
            assigned_team=assigned_team,
            queue=analysis.queue,
            escalation_required=analysis.escalation_required,
            sla_hours=sla_hours,
            sla_deadline=sla_deadline,
            first_response_sla_minutes=(
                first_response_minutes
            ),

            first_response_deadline=(
                first_response_deadline
            ),

            sla_total_paused_seconds=0,
            created_at=created_at,
            routing_reason=analysis.routing_reason,
            assigned_agent_id=assignment["agent"].id if assignment else None,
            assigned_agent_name=assignment["agent"].name if assignment else None,
            assignment_score=assignment["score"] if assignment else None,
            assignment_explanation=assignment["explanation"] if assignment else "No active agent available in team.",
        )
        db.add(ticket)
        db.flush()
        db.add(TicketEvent(ticket_id=ticket.id, event_type="CREATED", to_value="OPEN", notes="Ticket created and AI-analyzed."))
        if assignment:
            db.add(TicketEvent(ticket_id=ticket.id, event_type="AUTO_ASSIGNED", to_value=assignment["agent"].name, notes=assignment["explanation"]))
        db.commit()
        db.refresh(ticket)
        return ticket
