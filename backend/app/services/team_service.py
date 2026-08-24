class TeamService:
    """
    Canonical team resolution for ticket routing.

    Historical tickets may contain legacy labels such as:
        General Support
        Finance Team
        Technical Support Team

    Workforce agents, however, belong to canonical operational teams.

    This service translates legacy routing labels into the
    operational team that should actually receive the ticket.
    """

    TEAM_ALIASES = {
        # --------------------------------------------------
        # Fraud
        # --------------------------------------------------
        "fraud investigation": "Fraud Investigation",
        "fraud investigation team": "Fraud Investigation",
        "fraud team": "Fraud Investigation",

        # --------------------------------------------------
        # Security
        # --------------------------------------------------
        "cyber security": "Cyber Security",
        "cyber security team": "Cyber Security",
        "security team": "Cyber Security",

        # --------------------------------------------------
        # Technical
        # --------------------------------------------------
        "technical support": "Technical Support",
        "technical support team": "Technical Support",
        "technical team": "Technical Support",

        # --------------------------------------------------
        # Finance
        # --------------------------------------------------
        "finance operations": "Finance Operations",
        "finance operations team": "Finance Operations",
        "finance team": "Finance Operations",
        "billing team": "Finance Operations",
        "refund operations": "Finance Operations",
        "refund operations team": "Finance Operations",

        # --------------------------------------------------
        # Infrastructure
        # --------------------------------------------------
        "site reliability": "Site Reliability",
        "site reliability team": "Site Reliability",
        "sre": "Site Reliability",
        "sre team": "Site Reliability",
    }

    # ------------------------------------------------------
    # Simple canonicalization
    # ------------------------------------------------------

    @classmethod
    def canonicalize(
        cls,
        team: str | None,
    ) -> str:

        if not team:
            return ""

        normalized = (
            " ".join(
                team.strip().lower().split()
            )
        )

        return cls.TEAM_ALIASES.get(
            normalized,
            team.strip(),
        )

    # ------------------------------------------------------
    # Exact team comparison
    # ------------------------------------------------------

    @classmethod
    def matches(
        cls,
        left: str | None,
        right: str | None,
    ) -> bool:

        return (
            cls.canonicalize(left).lower()
            == cls.canonicalize(right).lower()
        )

    # ------------------------------------------------------
    # Resolve legacy/general routing
    # ------------------------------------------------------

    @classmethod
    def resolve_for_assignment(
        cls,
        team: str | None,
        category: str | None = None,
        subcategory: str | None = None,
    ) -> str:

        canonical_team = cls.canonicalize(team)

        # --------------------------------------------------
        # Already a known operational team
        # --------------------------------------------------

        if canonical_team in {
            "Fraud Investigation",
            "Cyber Security",
            "Technical Support",
            "Finance Operations",
            "Site Reliability",
        }:
            return canonical_team

        category_value = (
            (category or "")
            .strip()
            .lower()
        )

        subcategory_value = (
            (subcategory or "")
            .strip()
            .lower()
        )

        combined = (
            f"{category_value} "
            f"{subcategory_value}"
        )

        # --------------------------------------------------
        # Security / privacy
        # --------------------------------------------------

        if (
            category_value in {
                "security",
                "data privacy",
                "cyber security",
                "privacy",
            }
            or any(
                keyword in combined
                for keyword in [
                    "privacy",
                    "personal information",
                    "unauthorized access",
                    "credential compromise",
                    "account compromise",
                    "security incident",
                ]
            )
        ):
            return "Cyber Security"

        # --------------------------------------------------
        # Fraud
        # --------------------------------------------------

        if (
            category_value == "fraud"
            or any(
                keyword in combined
                for keyword in [
                    "fraud",
                    "unauthorized payment",
                    "suspicious transaction",
                    "transaction dispute",
                ]
            )
        ):
            return "Fraud Investigation"

        # --------------------------------------------------
        # Finance / billing / subscription / refund
        # --------------------------------------------------

        if (
            category_value in {
                "billing",
                "subscription",
                "refund",
                "payment",
                "finance",
            }
            or any(
                keyword in combined
                for keyword in [
                    "payment",
                    "refund",
                    "billing",
                    "invoice",
                    "subscription",
                    "duplicate charge",
                    "activation issue",
                ]
            )
        ):
            return "Finance Operations"

        # --------------------------------------------------
        # Infrastructure / outage
        # --------------------------------------------------

        if (
            category_value in {
                "service outage",
                "infrastructure",
                "site reliability",
            }
            or any(
                keyword in combined
                for keyword in [
                    "outage",
                    "availability",
                    "infrastructure",
                    "service unavailable",
                    "website unavailable",
                ]
            )
        ):
            return "Site Reliability"

        # --------------------------------------------------
        # Technical fallback
        # --------------------------------------------------

        if (
            category_value in {
                "technical",
                "account access",
                "customer service",
                "general support",
                "compliance",
            }
            or any(
                keyword in combined
                for keyword in [
                    "login",
                    "password",
                    "account access",
                    "internet",
                    "connectivity",
                    "application",
                    "portal",
                    "troubleshooting",
                ]
            )
        ):
            return "Technical Support"

        # --------------------------------------------------
        # Final enterprise fallback
        #
        # We currently do not have a dedicated
        # General Support workforce.
        #
        # Technical Support acts as the operational
        # fallback queue.
        # --------------------------------------------------

        return "Technical Support"