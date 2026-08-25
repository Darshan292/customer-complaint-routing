from __future__ import annotations

import json

from app.core.config import settings
from app.services.groq_service import client


class AIResolutionService:
    """Resolver-facing troubleshooting guidance grounded in retrieved evidence."""

    @staticmethod
    def _context_block(context: dict) -> str:
        sections = []

        sections.append("\n=== HISTORICAL RESOLVED/CLOSED TICKETS ===")
        for item in context.get("tickets", []):
            sections.append(
                f"Ticket #{item.get('ticket_id')} | {item.get('title')}\n"
                f"Status: {item.get('status')} | Category: {item.get('category')} | Subcategory: {item.get('subcategory')}\n"
                f"Historical resolver: {item.get('assigned_agent_name')}\n"
                f"Complaint: {item.get('complaint_text')}\n"
                f"Historical record:\n{item.get('content', '')[:3500]}"
            )

        sections.append("\n=== CONTROLLED SOP CONTEXT ===")
        for item in context.get("sop", []):
            sections.append(
                f"{item.get('title')} | {item.get('article_id') or item.get('source_id')}\n"
                f"{item.get('content', '')[:5000]}"
            )

        sections.append("\n=== CONTROLLED KNOWLEDGE BASE CONTEXT ===")
        for item in context.get("kb", []):
            sections.append(
                f"{item.get('title')} | {item.get('article_id') or item.get('source_id')}\n"
                f"{item.get('content', '')[:5000]}"
            )

        return "\n\n".join(sections)

    @staticmethod
    def recommend(ticket, context: dict) -> dict:
        retrieved_context = AIResolutionService._context_block(context)

        prompt = f"""
You are an enterprise service-desk resolution copilot helping a resolver solve a customer ticket.

The current ticket is the authoritative state of the incident. Retrieved sources are evidence only.
Use the following source precedence:
1. Current ticket and current system facts.
2. Controlled SOP procedure.
3. Controlled Knowledge Base procedure.
4. Historical resolved/closed tickets as precedent only.

Do not invent customer-specific facts, system access, successful actions, logs, configuration values,
or policy exceptions. Do not claim that a remediation has already happened. If evidence conflicts,
state the conflict and prefer the controlled SOP/KB over historical ticket precedent.

Return ONLY valid JSON with exactly these keys:

{{
  "summary": "short evidence-grounded diagnosis",
  "likely_root_cause": "most likely cause or best hypothesis",
  "recommended_steps": ["step 1", "step 2", "step 3"],
  "verification": ["how the resolver should verify the fix"],
  "customer_response": "concise suggested response to the customer",
  "confidence": 0.0,
  "caution": "important limitation or escalation condition",
  "source_references": [
    {{"type":"SOP|KB|TICKET", "id":"source identifier", "reason":"why it was relevant"}}
  ]
}}

CURRENT TICKET
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

RETRIEVED RESOLUTION CONTEXT
{retrieved_context}
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
                        "Use retrieved context as evidence and keep the recommendation "
                        "auditable and grounded."
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
            "source_references": data.get("source_references", []),
        }
