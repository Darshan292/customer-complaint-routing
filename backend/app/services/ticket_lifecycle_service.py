class TicketLifecycleService:

    ACTIVE_STATUSES = {
        "OPEN",
        "IN_PROGRESS",
        "PENDING_CUSTOMER",
    }

    TERMINAL_STATUSES = {
        "RESOLVED",
        "CLOSED",
    }

    VALID_STATUSES = {
        "OPEN",
        "IN_PROGRESS",
        "PENDING_CUSTOMER",
        "RESOLVED",
        "CLOSED",
    }

    VALID_TRANSITIONS = {
        "OPEN": {
            "IN_PROGRESS",
            "PENDING_CUSTOMER",
            "RESOLVED",
        },

        "IN_PROGRESS": {
            "PENDING_CUSTOMER",
            "RESOLVED",
        },

        "PENDING_CUSTOMER": {
            "IN_PROGRESS",
            "RESOLVED",
        },

        "RESOLVED": {
            "CLOSED",
            "IN_PROGRESS",
        },

        "CLOSED": {
            # Explicitly no normal transition.
            # Reopening must be a separate operation.
        },
    }

    @classmethod
    def validate_transition(
        cls,
        current_status: str,
        new_status: str,
    ):

        if new_status not in cls.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {new_status}"
            )

        allowed = cls.VALID_TRANSITIONS.get(
            current_status,
            set(),
        )

        if new_status not in allowed:
            raise ValueError(
                (
                    f"Invalid lifecycle transition: "
                    f"{current_status} → "
                    f"{new_status}"
                )
            )

    @classmethod
    def is_terminal(
        cls,
        status: str,
    ) -> bool:

        return (
            status
            in cls.TERMINAL_STATUSES
        )

    @classmethod
    def is_active(
        cls,
        status: str,
    ) -> bool:

        return (
            status
            in cls.ACTIVE_STATUSES
        )