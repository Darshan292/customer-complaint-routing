from datetime import datetime

from app.database.db import SessionLocal

# IMPORTANT:
# Import all models that participate in foreign keys
# before SQLAlchemy performs a flush/commit.
from app.models.agent import Agent
from app.models.complaint import Complaint
from app.models.team import Team
from app.models.ticket_event import TicketEvent

from app.services.sla_service import SLAService


def main():

    db = SessionLocal()

    try:

        tickets = (
            db.query(Complaint)
            .filter(
                Complaint.sla_deadline.is_(None),
                Complaint.status.notin_(
                    [
                        "CLOSED",
                    ]
                ),
            )
            .all()
        )

        updated = 0

        for ticket in tickets:

            if not ticket.priority_level:
                continue

            start_time = (
                ticket.created_at
                or datetime.utcnow()
            )

            ticket.sla_hours = (
                SLAService.get_sla_hours(
                    ticket.priority_level
                )
            )

            ticket.sla_deadline = (
                SLAService.calculate_deadline(
                    priority_level=(
                        ticket.priority_level
                    ),
                    started_at=start_time,
                    timezone_name="Asia/Kolkata",
                )
            )

            updated += 1

            print(
                f"[UPDATED] Ticket "
                f"#{ticket.id} | "
                f"{ticket.priority_level} | "
                f"{ticket.sla_deadline}"
            )

        db.commit()

        print()
        print(
            "======================================"
        )
        print(
            "SLA BACKFILL COMPLETED"
        )
        print(
            "======================================"
        )
        print(
            f"Updated {updated} tickets."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()