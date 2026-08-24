import json

from groq import Groq

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


class GroqService:

    @staticmethod
    def analyze_complaint(text: str):

        prompt = f"""
You are an enterprise complaint analysis engine.

Analyze the complaint.

Return ONLY valid JSON.

Allowed categories:

Billing
Technical
Product Defect
Account Access
Fraud
Security
Refund
Delivery
Subscription
Data Privacy
Service Outage
Compliance
Customer Service
Feature Request
Other

business_impact MUST be one of:
Low
Medium
High

emotion MUST be one of:
Anger
Fear
Frustration
Confusion
Satisfaction
Urgency
Disappointment
Neutral

Return format:

{{
  "category":"",
  "subcategory":"",
  "sentiment":"",
  "emotion":"",
  "business_impact":"",
  "customer_intent":"",
  "summary":"",
  "confidence":0.0,
  "keywords":[],
  "routing_reason":""
}}

Complaint:
{text}
"""

        response = client.chat.completions.create(
            model=settings.MODEL_NAME,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content