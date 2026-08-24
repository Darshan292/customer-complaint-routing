"""Repair legacy ticket states created before assignment/lifecycle rules were enforced."""
from app.database.db import SessionLocal
from app.models.complaint import Complaint
from app.models.agent import Agent
from app.models.ticket_event import TicketEvent
from datetime import datetime


def main():
    db = SessionLocal()
    try:
        tickets = (
            db.query(Complaint)
            .filter(
                Complaint.status.in_(["IN_PROGRESS", "PENDING_CUSTOMER"]),
                Complaint.assigned_agent_id.is_(None),
            )
            .all()
        )

        repaired = []
        for ticket in tickets:
            previous = ticket.status
            ticket.status = "OPEN"
            ticket.updated_at = datetime.utcnow()
            db.add(
                TicketEvent(
                    ticket_id=ticket.id,
                    event_type="STATE_REPAIRED",
                    from_value=previous,
                    to_value="OPEN",
                    notes=(
                        "Legacy inconsistent state repaired: "
                        "unassigned active ticket returned to OPEN queue."
                    ),
                )
            )
            repaired.append(ticket.id)

        db.commit()
        print(f"Repaired {len(repaired)} ticket(s): {repaired}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
