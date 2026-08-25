from __future__ import annotations


class SimilarTicketService:
    """Compatibility facade over the enterprise hybrid retrieval service."""

    @classmethod
    def find_similar(
        cls,
        ticket,
        resolved_tickets: list,
        limit: int = 5,
        db=None,
    ) -> list[dict]:
        if db is None:
            return []

        from app.services.hybrid_retrieval_service import HybridRetrievalService

        context = HybridRetrievalService.resolution_context(
            ticket,
            db,
            ticket_limit=limit,
            sop_limit=0,
            kb_limit=0,
        )

        output = []
        for item in context["tickets"]:
            output.append(
                {
                    "ticket_id": item.get("ticket_id"),
                    "similarity_score": float(item.get("rerank_score_normalized", 0.0)),
                    "category": item.get("category"),
                    "subcategory": item.get("subcategory"),
                    "priority_level": item.get("priority_level"),
                    "summary": item.get("summary"),
                    "complaint_text": item.get("complaint_text"),
                    "resolved_at": item.get("resolved_at"),
                    "assigned_agent_name": item.get("assigned_agent_name"),
                    "resolution_outcome": item.get("content"),
                    "status": item.get("status"),
                    "dense_score": item.get("dense_score"),
                    "sparse_score": item.get("sparse_score"),
                    "rerank_score": item.get("rerank_score"),
                }
            )
        return output
