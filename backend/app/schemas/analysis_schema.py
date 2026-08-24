from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime

class AnalysisResult(BaseModel):

    category: Literal[
        "Billing",
        "Technical",
        "Product Defect",
        "Account Access",
        "Fraud",
        "Security",
        "Refund",
        "Delivery",
        "Subscription",
        "Data Privacy",
        "Service Outage",
        "Compliance",
        "Customer Service",
        "Feature Request",
        "Other"
    ]

    subcategory: str

    sentiment: Literal[
        "Positive",
        "Neutral",
        "Negative"
    ]

    emotion: Literal[
        "Anger",
        "Fear",
        "Frustration",
        "Confusion",
        "Satisfaction",
        "Urgency",
        "Disappointment",
        "Neutral"
    ]

    business_impact: Literal[
        "Low",
        "Medium",
        "High"
    ]

    customer_intent: str

    summary: str

    confidence: float

    keywords: List[str] 

    routing_reason : str

    priority_score: float | None = None

    priority_level: str | None = None
    priority_source: str | None = None

    sla_hours: int | None = None 
    

    sla_deadline: datetime | None = None

    assigned_team: str | None = None

    queue: str | None = None

    escalation_required: bool | None = None