class PriorityService:
    """Deterministic priority policy with an optional customer-selected floor."""

    LEVEL_SCORE = {"Low": 25, "Medium": 50, "High": 75, "Critical": 95}
    SLA_HOURS = {"Low": 48, "Medium": 24, "High": 8, "Critical": 4}

    CATEGORY_WEIGHTS = {
        "Fraud": 30, "Security": 30, "Data Privacy": 30,
        "Service Outage": 28, "Compliance": 25, "Product Defect": 20,
        "Technical": 15, "Billing": 12, "Refund": 12, "Customer Service": 8,
        "Feature Request": 5, "Other": 5,
    }
    IMPACT_WEIGHTS = {"High": 25, "Medium": 15, "Low": 5}
    SENTIMENT_WEIGHTS = {"Negative": 12, "Neutral": 5, "Positive": 0}
    TIER_WEIGHTS = {"Platinum": 12, "Gold": 8, "Silver": 4, "Standard": 0}

    @classmethod
    def normalize_level(cls, level):
        if not level:
            return None
        value = str(level).strip().title()
        return value if value in cls.LEVEL_SCORE else None

    @classmethod
    def calculate_priority(cls, category, customer_tier, sentiment, business_impact, customer_priority=None):
        score = (
            cls.CATEGORY_WEIGHTS.get(category, 5)
            + cls.IMPACT_WEIGHTS.get(business_impact, 5)
            + cls.SENTIMENT_WEIGHTS.get(sentiment, 5)
            + cls.TIER_WEIGHTS.get(customer_tier, 0)
        )
        score = min(100, score)
        ai_level = "Critical" if score >= 80 else "High" if score >= 60 else "Medium" if score >= 35 else "Low"

        requested = cls.normalize_level(customer_priority)
        if requested:
            # Customer selection acts as a requested level, never as a way to downgrade
            # a materially risky AI classification.
            if cls.LEVEL_SCORE[requested] >= cls.LEVEL_SCORE[ai_level]:
                final_level = requested
                source = "CUSTOMER"
            else:
                final_level = ai_level
                source = "AI_SAFETY_OVERRIDE"
        else:
            final_level = ai_level
            source = "AI"

        return {
            "priority_score": max(score, cls.LEVEL_SCORE[final_level] if source == "CUSTOMER" else score),
            "priority_level": final_level,
            "priority_source": source,
            "sla_hours": cls.SLA_HOURS[final_level],
            "reason": f"AI={ai_level}; customer_request={requested or 'not provided'}; final={final_level}",
        }
