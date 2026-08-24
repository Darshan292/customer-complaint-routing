from __future__ import annotations

from collections import Counter
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SimilarTicketService:
    """Finds previously resolved/closed tickets similar to the current ticket."""

    @staticmethod
    def _text(ticket) -> str:
        parts = [
            ticket.category,
            ticket.subcategory,
            ticket.summary,
            ticket.routing_reason,
            ticket.complaint_text,
            ticket.customer_intent,
            ticket.keywords,
        ]
        return " ".join(
            str(part).strip()
            for part in parts
            if part
        )

    @classmethod
    def find_similar(
        cls,
        ticket,
        resolved_tickets: list,
        limit: int = 5,
    ) -> list[dict]:
        if not resolved_tickets:
            return []

        corpus = [cls._text(ticket)] + [
            cls._text(item)
            for item in resolved_tickets
        ]

        try:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000,
            )
            matrix = vectorizer.fit_transform(corpus)
            scores = cosine_similarity(
                matrix[0:1],
                matrix[1:],
            )[0]
        except ValueError:
            scores = [0.0] * len(resolved_tickets)

        ranked = []

        query_category = (ticket.category or "").strip().lower()
        query_subcategory = (ticket.subcategory or "").strip().lower()

        for item, score in zip(resolved_tickets, scores):
            category_bonus = 0.0
            if query_category and query_category == (item.category or "").strip().lower():
                category_bonus += 0.10
            if query_subcategory and query_subcategory == (item.subcategory or "").strip().lower():
                category_bonus += 0.12

            final_score = min(1.0, float(score) + category_bonus)

            ranked.append(
                {
                    "ticket_id": item.id,
                    "similarity_score": round(final_score, 3),
                    "category": item.category,
                    "subcategory": item.subcategory,
                    "priority_level": item.priority_level,
                    "summary": item.summary,
                    "complaint_text": item.complaint_text,
                    "resolved_at": item.resolved_at,
                    "assigned_agent_name": item.assigned_agent_name,
                    "resolution_outcome": (
                        item.resolution_summary
                        if hasattr(item, "resolution_summary")
                        else None
                    ),
                    "status": item.status,
                }
            )

        ranked.sort(
            key=lambda item: item["similarity_score"],
            reverse=True,
        )

        # Only show meaningful similarities. If the corpus is weak, the resolver
        # should see an empty list rather than unrelated old tickets.
        return [
            item
            for item in ranked[:limit]
            if item["similarity_score"] >= 0.08
        ]
