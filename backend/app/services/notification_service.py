from datetime import datetime

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.models.agent import Agent


class NotificationService:
    """Creates persistent in-app notifications for operational events."""

    @staticmethod
    def create(
        db: Session,
        *,
        recipient_id: int,
        recipient_role: str,
        notification_type: str,
        title: str,
        message: str,
        ticket_id: int | None = None,
    ) -> Notification:

        notification = Notification(
            recipient_id=recipient_id,
            recipient_role=recipient_role,
            notification_type=notification_type,
            title=title,
            message=message,
            ticket_id=ticket_id,
            is_read=False,
        )

        db.add(notification)
        return notification

    @classmethod
    def customer(
        cls,
        db: Session,
        ticket,
        *,
        notification_type: str,
        title: str,
        message: str,
    ) -> None:

        if not ticket.customer_name:
            return

        user = (
            db.query(User)
            .filter(
                User.name == ticket.customer_name,
                User.role.in_(["customer", "user"]),
            )
            .first()
        )

        if not user:
            return

        cls.create(
            db,
            recipient_id=user.id,
            recipient_role="customer",
            notification_type=notification_type,
            title=title,
            message=message,
            ticket_id=ticket.id,
        )

    @classmethod
    def resolver(
        cls,
        db: Session,
        agent_id: int | None,
        *,
        notification_type: str,
        title: str,
        message: str,
        ticket_id: int | None,
    ) -> None:

        if not agent_id:
            return

        agent = (
            db.query(Agent)
            .filter(
                Agent.id == agent_id,
                Agent.active.is_(True),
            )
            .first()
        )

        if not agent:
            return

        cls.create(
            db,
            recipient_id=agent.id,
            recipient_role="agent",
            notification_type=notification_type,
            title=title,
            message=message,
            ticket_id=ticket_id,
        )

    @classmethod
    def assignment(
        cls,
        db: Session,
        ticket,
        *,
        agent_id: int,
        agent_name: str,
        mode: str = "AUTO",
        previous_agent_id: int | None = None,
    ) -> None:

        verb = (
            "automatically assigned"
            if mode == "AUTO"
            else "assigned to you"
        )

        cls.customer(
            db,
            ticket,
            notification_type="TICKET_ASSIGNED",
            title=f"Ticket #{ticket.id} assigned",
            message=(
                f"Your ticket has been {verb} "
                f"to {agent_name}."
            ),
        )

        cls.resolver(
            db,
            agent_id,
            notification_type="TICKET_ASSIGNED",
            title=f"Ticket #{ticket.id} assigned to you",
            message=(
                f"You are now responsible for ticket #{ticket.id}: "
                f"{ticket.summary or ticket.category or 'Customer complaint'}."
            ),
            ticket_id=ticket.id,
        )

        if (
            previous_agent_id
            and previous_agent_id != agent_id
        ):
            cls.resolver(
                db,
                previous_agent_id,
                notification_type="TICKET_REASSIGNED",
                title=f"Ticket #{ticket.id} reassigned",
                message=(
                    f"Ticket #{ticket.id} has been reassigned "
                    f"to {agent_name}."
                ),
                ticket_id=ticket.id,
            )

    @classmethod
    def status_change(
        cls,
        db: Session,
        ticket,
        previous_status: str,
        new_status: str,
    ) -> None:

        pretty = (
            new_status.replace("_", " ").title()
        )

        customer_message = {
            "IN_PROGRESS": (
                f"Ticket #{ticket.id} is now being worked on "
                f"by {ticket.assigned_agent_name or 'the support team'}."
            ),
            "PENDING_CUSTOMER": (
                f"Ticket #{ticket.id} is waiting for information "
                f"from you."
            ),
            "RESOLVED": (
                f"Ticket #{ticket.id} has been marked resolved."
            ),
            "CLOSED": (
                f"Ticket #{ticket.id} has been closed."
            ),
            "OPEN": (
                f"Ticket #{ticket.id} is open and waiting in the support queue."
            ),
        }.get(
            new_status,
            f"Ticket #{ticket.id} status changed to {pretty}.",
        )

        cls.customer(
            db,
            ticket,
            notification_type="STATUS_CHANGED",
            title=f"Ticket #{ticket.id} status updated",
            message=customer_message,
        )

        cls.resolver(
            db,
            ticket.assigned_agent_id,
            notification_type="STATUS_CHANGED",
            title=f"Ticket #{ticket.id} status changed",
            message=(
                f"Ticket #{ticket.id} changed from "
                f"{previous_status.replace('_', ' ').title()} "
                f"to {pretty}."
            ),
            ticket_id=ticket.id,
        )

    @classmethod
    def priority_change(
        cls,
        db: Session,
        ticket,
        previous_priority: str,
        new_priority: str,
    ) -> None:

        message = (
            f"Ticket #{ticket.id} priority changed from "
            f"{previous_priority or 'Unspecified'} to {new_priority}."
        )

        cls.customer(
            db,
            ticket,
            notification_type="PRIORITY_CHANGED",
            title=f"Ticket #{ticket.id} priority updated",
            message=message,
        )

        cls.resolver(
            db,
            ticket.assigned_agent_id,
            notification_type="PRIORITY_CHANGED",
            title=f"Ticket #{ticket.id} priority updated",
            message=message,
            ticket_id=ticket.id,
        )
