from datetime import datetime


class EscalationService:

    # --------------------------------------------------
    # Escalation thresholds
    # --------------------------------------------------

    FIRST_RESPONSE_ESCALATION = {
        "Low": 0,
        "Medium": 1,
        "High": 1,
        "Critical": 1,
    }

    RESOLUTION_ESCALATION = {
        "Low": 1,
        "Medium": 1,
        "High": 1,
        "Critical": 1,
    }

    PRIORITY_ESCALATION = {
        "Low": False,
        "Medium": False,
        "High": True,
        "Critical": True,
    }

    @classmethod
    def determine(
        cls,
        ticket,
        first_response_state: str,
        resolution_state: str,
    ) -> dict:

        reasons = []

        level = ticket.escalation_level or 0

        # --------------------------------------------------
        # Critical tickets
        # --------------------------------------------------

        if (
            ticket.priority_level
            == "Critical"
        ):
            reasons.append(
                "Critical priority requires elevated operational attention."
            )

            level = max(
                level,
                1,
            )

        # --------------------------------------------------
        # First response breach
        # --------------------------------------------------

        if first_response_state == "BREACHED":

            reasons.append(
                "First-response SLA breached."
            )

            level = max(
                level,
                1,
            )

        # --------------------------------------------------
        # Resolution breach
        # --------------------------------------------------

        if resolution_state == "BREACHED":

            reasons.append(
                "Resolution SLA breached."
            )

            level = max(
                level,
                2,
            )

        # --------------------------------------------------
        # At-risk Critical ticket
        # --------------------------------------------------

        if (
            ticket.priority_level
            == "Critical"
            and resolution_state
            == "AT_RISK"
        ):

            reasons.append(
                "Critical ticket is approaching resolution SLA breach."
            )

            level = max(
                level,
                1,
            )

        # --------------------------------------------------
        # Escalation decision
        # --------------------------------------------------

        should_escalate = (
            level > (
                ticket.escalation_level
                or 0
            )
        )

        if not reasons:
            return {
                "should_escalate": False,
                "level": (
                    ticket.escalation_level
                    or 0
                ),
                "reason": None,
                "owner": None,
            }

        owner = cls.determine_owner(
            ticket,
            level,
        )

        return {
            "should_escalate": (
                should_escalate
            ),
            "level": level,
            "reason": " ".join(
                reasons
            ),
            "owner": owner,
        }

    @classmethod
    def determine_owner(
        cls,
        ticket,
        level: int,
    ) -> str:

        if level >= 3:
            return "INCIDENT_MANAGEMENT"

        if level == 2:
            return "OPERATIONS_MANAGER"

        if level == 1:
            if ticket.assigned_agent_name:
                return "TEAM_SUPERVISOR"

            return "ON_CALL_SUPERVISOR"

        return "UNASSIGNED"

    @classmethod
    def apply(
        cls,
        ticket,
        decision: dict,
    ):

        if not decision[
            "should_escalate"
        ]:
            return False

        ticket.escalation_level = (
            decision["level"]
        )

        ticket.escalated_at = (
            datetime.utcnow()
        )

        ticket.escalation_reason = (
            decision["reason"]
        )

        ticket.escalation_owner = (
            decision["owner"]
        )

        ticket.escalation_count = (
            (ticket.escalation_count or 0)
            + 1
        )

        ticket.escalation_required = True

        return True