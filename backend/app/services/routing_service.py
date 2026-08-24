class RoutingService:
    TEAM_MAPPING = {
        "Fraud": {"team": "Fraud Investigation", "queue": "FRAUD-L1"},
        "Security": {"team": "Cyber Security", "queue": "SECURITY-L1"},
        "Technical": {"team": "Technical Support", "queue": "TECH-L1"},
        "Billing": {"team": "Finance Operations", "queue": "BILLING-L1"},
        "Refund": {"team": "Refund Operations", "queue": "REFUND-L1"},
        "Service Outage": {"team": "Site Reliability", "queue": "SRE-L1"},
        "Data Privacy": {"team": "Data Privacy", "queue": "PRIVACY-L1"},
        "Compliance": {"team": "Compliance", "queue": "COMPLIANCE-L1"},
    }

    @classmethod
    def route(cls, category, priority_level):
        routing = cls.TEAM_MAPPING.get(category, {"team": "General Support", "queue": "GENERAL-L1"})
        return {
            "assigned_team": routing["team"],
            "queue": routing["queue"],
            "escalation_required": priority_level == "Critical",
        }
