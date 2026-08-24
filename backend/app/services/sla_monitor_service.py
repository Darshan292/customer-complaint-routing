from datetime import datetime

from app.models.complaint import Complaint
from app.models.ticket_event import TicketEvent

from app.services.escalation_service import (
    EscalationService,
)

from app.services.sla_service import (
    SLAService,
)


class SLAMonitorService:

    @classmethod
    def evaluate_ticket(
        cls,
        ticket: Complaint,
    ) -> dict:

        now = datetime.utcnow()

        first_response = (
            SLAService.evaluate_first_response(
                priority_level=(
                    ticket.priority_level
                ),
                deadline=(
                    ticket.first_response_deadline
                ),
                responded_at=(
                    ticket.first_response_at
                ),
            )
        )

        resolution = (
            SLAService.evaluate_resolution(
                priority_level=(
                    ticket.priority_level
                ),
                deadline=(
                    ticket.sla_deadline
                ),
            )
        )

        escalation = (
            EscalationService.determine(
                ticket=ticket,
                first_response_state=(
                    first_response["state"]
                ),
                resolution_state=(
                    resolution["state"]
                ),
            )
        )

        return {
            "ticket_id": ticket.id,
            "first_response": (
                first_response
            ),
            "resolution": resolution,
            "escalation": escalation,
            "evaluated_at": now,
        }

    @classmethod
    def apply_ticket(
        cls,
        ticket: Complaint,
        db,
    ) -> dict:

        result = cls.evaluate_ticket(
            ticket
        )

        previous_level = (
            ticket.escalation_level
            or 0
        )

        escalated = (
            EscalationService.apply(
                ticket,
                result["escalation"],
            )
        )

        if escalated:

            db.add(
                TicketEvent(
                    ticket_id=ticket.id,
                    event_type="SLA_ESCALATED",
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

        return result