from datetime import datetime
from app.services.groq_service import GroqService
from app.services.parser_service import ParserService
from app.services.priority_service import PriorityService
from app.services.sla_service import SLAService
from app.services.classification_service import ClassificationService
from app.services.routing_service import RoutingService
from app.services.assignment_service import AssignmentService


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

        routing = RoutingService.route(parsed.category, parsed.priority_level)
        parsed.assigned_team = routing["assigned_team"]
        parsed.queue = routing["queue"]
        parsed.escalation_required = routing["escalation_required"]
        parsed.routing_reason = f"{parsed.routing_reason} | {priority['reason']}"

        assignment = AssignmentService.choose_agent(
            db, parsed.assigned_team, parsed.category, parsed.subcategory, parsed.priority_level
        )
        return parsed, assignment
