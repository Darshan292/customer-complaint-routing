from datetime import datetime
from app.services.groq_service import GroqService
from app.services.parser_service import ParserService
from app.services.priority_service import PriorityService
from app.services.sla_service import SLAService
from app.services.classification_service import ClassificationService
from app.services.routing_service import RoutingService
from app.services.assignment_service import AssignmentService
from app.models.agent import Agent
from app.core.config import settings


class AnalysisService:
    @staticmethod
    def analyze(text: str, customer_tier: str, customer_priority: str | None, db):
        raw = GroqService.analyze_complaint(text)
        parsed = ParserService.parse(raw)
        parsed.category = ClassificationService.get_final_category(text, parsed.category)

        priority = PriorityService.calculate_priority(
            category=parsed.category,
            customer_tier=customer_tier,
            sentiment=parsed.sentiment,
            business_impact=parsed.business_impact,
            customer_priority=customer_priority,
        )
        parsed.priority_score = priority["priority_score"]
        parsed.priority_level = priority["priority_level"]
        parsed.priority_source = priority["priority_source"]
        parsed.sla_hours = priority["sla_hours"]
        parsed.sla_deadline = SLAService.calculate_deadline(parsed.priority_level, datetime.utcnow())

        # Temporary Workday Cost Center EIB workflow.
        # This is intentionally deterministic: if the complaint explicitly
        # requests cost-center creation and includes the EIB attachment, route
        # it to Priya (configured by WD_COST_CENTER_AGENT_ID).
        is_cost_center_eib = (
            "cost center" in text.lower()
            and "creation" in text.lower()
        )

        routing = RoutingService.route(parsed.category, parsed.priority_level)
        if is_cost_center_eib:
            routing = {
                "assigned_team": "Technical Support",
                "queue": "TECH-L1",
                "escalation_required": parsed.priority_level == "Critical",
            }
            parsed.subcategory = "Workday Cost Center EIB"
            parsed.routing_reason = f"Temporary Workday Cost Center EIB workflow | {parsed.routing_reason}"

        parsed.assigned_team = routing["assigned_team"]
        parsed.queue = routing["queue"]
        parsed.escalation_required = routing["escalation_required"]
        parsed.routing_reason = f"{parsed.routing_reason} | {priority['reason']}"

        assignment = None
        if is_cost_center_eib:
            target = db.query(Agent).filter(Agent.id == settings.WD_COST_CENTER_AGENT_ID, Agent.active.is_(True)).first()
            if target:
                assignment = {
                    "agent": target,
                    "score": 100.0,
                    "explanation": "Temporary Workday Cost Center EIB workflow: assigned directly to the configured Cost Center EIB resolver for EIB launch handling.",
                }
        else:
            assignment = AssignmentService.choose_agent(
                db, parsed.assigned_team, parsed.category, parsed.subcategory, parsed.priority_level
            )
        return parsed, assignment
