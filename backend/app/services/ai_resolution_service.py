from __future__ import annotations

import json

from app.core.config import settings
from app.services.groq_service import client


class AIResolutionService:
    """Generates resolver-facing troubleshooting guidance with Groq."""

    @staticmethod
    def recommend(ticket) -> dict:
        prompt = f"""
You are an enterprise service-desk resolution copilot helping a resolver solve a customer ticket.

Use ONLY the information in the ticket below. Do not invent customer-specific facts, system access,
or successful actions that are not present in the ticket.

Return ONLY valid JSON with exactly these keys:

{{
  "summary": "short diagnosis",
  "likely_root_cause": "most likely cause or best hypothesis",
  "recommended_steps": [
    "step 1",
    "step 2",
    "step 3"
  ],
  "verification": [
    "how the resolver should verify the fix"
  ],
  "customer_response": "concise suggested response to the customer",
  "confidence": 0.0,
  "caution": "important limitation or escalation condition"
}}

Ticket:
ID: {ticket.id}
Category: {ticket.category}
Subcategory: {ticket.subcategory}
Priority: {ticket.priority_level}
Business impact: {ticket.business_impact}
Sentiment: {ticket.sentiment}
Emotion: {ticket.emotion}
Customer intent: {ticket.customer_intent}
Summary: {ticket.summary}
Routing reason: {ticket.routing_reason}
Customer complaint:
{ticket.complaint_text}
"""

        response = client.chat.completions.create(
            model=settings.MODEL_NAME,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cautious enterprise support resolution copilot. "
                        "Provide practical troubleshooting guidance, not fabricated facts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)

        return {
            "summary": data.get("summary", ""),
            "likely_root_cause": data.get("likely_root_cause", ""),
            "recommended_steps": data.get("recommended_steps", []),
            "verification": data.get("verification", []),
            "customer_response": data.get("customer_response", ""),
            "confidence": float(data.get("confidence", 0) or 0),
            "caution": data.get("caution", ""),
        }
