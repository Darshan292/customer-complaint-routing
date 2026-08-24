from datetime import datetime
from app.database.db import SessionLocal

# IMPORTANT:
# Register all ORM models before SQLAlchemy performs
# any flush/commit involving Complaint foreign keys.
from app.models.user import User
from app.models.complaint import Complaint
from app.models.agent import Agent
from app.models.team import Team
from app.models.ticket_event import TicketEvent

from app.services.sla_service import SLAService


def main():

    db = SessionLocal()

    try:

        tickets = (
            db.query(Complaint)
            .filter(
                Complaint.first_response_deadline.is_(None),
                Complaint.status.notin_(
                    ["CLOSED"]
                ),
            )
            .all()
        )

        updated = 0

        for ticket in tickets:

            if not ticket.priority_level:
                continue

            start = (
                ticket.created_at
                or datetime.utcnow()
            )

            minutes = (
                SLAService.get_first_response_minutes(
                    ticket.priority_level
                )
            )

            ticket.first_response_sla_minutes = (
                minutes
            )

            ticket.first_response_deadline = (
                SLAService.calculate_first_response_deadline(
                    priority_level=(
                        ticket.priority_level
                    ),
                    started_at=start,
                    timezone_name="Asia/Kolkata",
                )
            )

            updated += 1

            print(
                f"[UPDATED] Ticket "
                f"#{ticket.id} | "
                f"{ticket.priority_level} | "
                f"{ticket.first_response_deadline}"
            )

        db.commit()

        print()
        print(
            "FIRST RESPONSE SLA BACKFILL COMPLETED"
        )
        print(
            f"Updated {updated} tickets."
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()