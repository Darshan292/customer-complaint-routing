from __future__ import annotations

import hashlib
import math
import pickle
import re
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings


class HybridRetrievalService:
    """
    Enterprise resolution-context retrieval:

      1. Dense semantic retrieval with SentenceTransformer + Qdrant.
      2. Sparse lexical retrieval with TF-IDF.
      3. Reciprocal Rank Fusion (RRF).
      4. Cross-encoder reranking of the fused shortlist.

    The same retrieval pipeline is used for historical tickets, SOP and KB.
    This keeps ranking behavior consistent while preserving source metadata.
    """

    COLLECTION = "resolution_context"
    RRF_K = 60

    _qdrant = None
    _embedder = None
    _reranker = None
    _sparse_vectorizer = None
    _sparse_matrix = None
    _sparse_records = None
    _initialized = False

    @classmethod
    def _knowledge_dir(cls) -> Path:
        return Path(settings.KNOWLEDGE_DIR)

    @classmethod
    def _index_dir(cls) -> Path:
        path = Path(settings.VECTOR_STORE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def _sparse_index_path(cls) -> Path:
        return cls._index_dir() / "sparse_index.pkl"

    @classmethod
    def _load_models(cls):
        if cls._embedder is None or cls._reranker is None:
            from sentence_transformers import CrossEncoder, SentenceTransformer

            cls._embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
            cls._reranker = CrossEncoder(settings.RERANKER_MODEL)

    @classmethod
    def _load_qdrant(cls):
        if cls._qdrant is None:
            from qdrant_client import QdrantClient

            cls._qdrant = QdrantClient(path=str(cls._index_dir() / "qdrant"))
        return cls._qdrant

    @classmethod
    def _point_id(cls, source_type: str, source_id: str) -> int:
        raw = f"{source_type}:{source_id}".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        return int(digest[:15], 16)

    @classmethod
    def _clean_text(cls, text: str) -> str:
        text = text.replace("\x0c", "\n\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def _page_documents(cls, path: Path, source_type: str) -> list[dict]:
        if not path.exists():
            return []

        raw = path.read_text(encoding="utf-8", errors="ignore")
        docs: list[dict] = []

        for page_index, page in enumerate(raw.split("\f"), start=1):
            text = cls._clean_text(page)
            if not text:
                continue

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            title = lines[1] if len(lines) > 1 else lines[0][:120]

            article_id = None
            for line in lines[:12]:
                match = re.search(r"\b(KB-[A-Z0-9-]+|SOP-[A-Z0-9-]+)\b", line)
                if match:
                    article_id = match.group(1)
                    break

            docs.append(
                {
                    "source_type": source_type,
                    "source_id": f"{source_type}-page-{page_index}",
                    "title": title[:180],
                    "text": text,
                    "page": page_index,
                    "article_id": article_id,
                }
            )

        return docs

    @classmethod
    def _split_ticket_text(cls, ticket, events: Iterable | None = None) -> str:
        event_lines = []
        for event in list(events or [])[-12:]:
            event_lines.append(
                " | ".join(
                    value
                    for value in [
                        event.event_type,
                        event.from_value,
                        event.to_value,
                        event.notes,
                    ]
                    if value
                )
            )

        return cls._clean_text(
            f"Ticket #{ticket.id}\n"
            f"Status: {ticket.status}\n"
            f"Category: {ticket.category}\n"
            f"Subcategory: {ticket.subcategory}\n"
            f"Priority: {ticket.priority_level}\n"
            f"Business impact: {ticket.business_impact}\n"
            f"Customer intent: {ticket.customer_intent}\n"
            f"Routing reason: {ticket.routing_reason}\n"
            f"Assigned team: {ticket.assigned_team}\n"
            f"Assigned resolver: {ticket.assigned_agent_name}\n"
            f"Summary: {ticket.summary}\n"
            f"Complaint: {ticket.complaint_text}\n"
            f"Resolution timestamp: {ticket.resolved_at}\n"
            f"Historical events:\n" + "\n".join(event_lines)
        )

    @classmethod
    def build_corpus(cls, db) -> list[dict]:
        from app.models.complaint import Complaint
        from app.models.ticket_event import TicketEvent

        documents = []

        # Governed documents are indexed as source-specific pages.
        documents.extend(
            cls._page_documents(
                Path(settings.SOP_PATH),
                "sop",
            )
        )
        documents.extend(
            cls._page_documents(
                Path(settings.KB_PATH),
                "kb",
            )
        )

        # Historical ticket dump = resolved/closed tickets from the operational DB.
        tickets = (
            db.query(Complaint)
            .filter(
                Complaint.status.in_(["RESOLVED", "CLOSED"])
            )
            .order_by(Complaint.resolved_at.desc(), Complaint.created_at.desc())
            .all()
        )

        for ticket in tickets:
            events = (
                db.query(TicketEvent)
                .filter(TicketEvent.ticket_id == ticket.id)
                .order_by(TicketEvent.created_at.asc())
                .all()
            )
            documents.append(
                {
                    "source_type": "ticket",
                    "source_id": str(ticket.id),
                    "title": f"Resolved Ticket #{ticket.id}: {ticket.summary or ticket.category or 'Historical case'}",
                    "text": cls._split_ticket_text(ticket, events),
                    "ticket_id": ticket.id,
                    "status": ticket.status,
                    "category": ticket.category,
                    "subcategory": ticket.subcategory,
                    "priority_level": ticket.priority_level,
                    "summary": ticket.summary,
                    "complaint_text": ticket.complaint_text,
                    "assigned_agent_name": ticket.assigned_agent_name,
                    "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                }
            )

        return documents

    @classmethod
    def rebuild(cls, db) -> dict:
        cls._load_models()
        client = cls._load_qdrant()

        documents = cls.build_corpus(db)
        if not documents:
            raise RuntimeError("No resolution-context documents are available to index.")

        existing = [collection.name for collection in client.get_collections().collections]
        if cls.COLLECTION in existing:
            client.delete_collection(cls.COLLECTION)

        dimension = len(
            cls._embedder.encode(
                "dimension probe",
                normalize_embeddings=True,
            )
        )

        from qdrant_client.models import Distance, PointStruct, VectorParams

        client.create_collection(
            collection_name=cls.COLLECTION,
            vectors_config=VectorParams(
                size=dimension,
                distance=Distance.COSINE,
            ),
        )

        texts = [doc["text"] for doc in documents]
        vectors = cls._embedder.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )

        points = []
        for doc, vector in zip(documents, vectors):
            payload = dict(doc)
            points.append(
                PointStruct(
                    id=cls._point_id(
                        doc["source_type"],
                        doc["source_id"],
                    ),
                    vector=vector.tolist(),
                    payload=payload,
                )
            )

        client.upsert(
            collection_name=cls.COLLECTION,
            points=points,
            wait=True,
        )

        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=10000,
            sublinear_tf=True,
        )
        sparse_matrix = vectorizer.fit_transform(texts)

        with cls._sparse_index_path().open("wb") as handle:
            pickle.dump(
                {
                    "vectorizer": vectorizer,
                    "matrix": sparse_matrix,
                    "records": [
                        {
                            "point_key": f"{doc['source_type']}:{doc['source_id']}",
                            "source_type": doc["source_type"],
                            "source_id": doc["source_id"],
                        }
                        for doc in documents
                    ],
                    "version": 1,
                },
                handle,
            )

        cls._sparse_vectorizer = vectorizer
        cls._sparse_matrix = sparse_matrix
        cls._sparse_records = documents
        cls._initialized = True

        return {
            "documents": len(documents),
            "tickets": sum(doc["source_type"] == "ticket" for doc in documents),
            "sop": sum(doc["source_type"] == "sop" for doc in documents),
            "kb": sum(doc["source_type"] == "kb" for doc in documents),
            "embedding_model": settings.EMBEDDING_MODEL,
            "reranker_model": settings.RERANKER_MODEL,
            "method": "dense + TF-IDF + RRF + cross-encoder reranking",
        }

    @classmethod
    def _load_sparse_index(cls):
        if cls._sparse_vectorizer is not None:
            return

        path = cls._sparse_index_path()
        if not path.exists():
            raise RuntimeError("Resolution retrieval index has not been built yet.")

        with path.open("rb") as handle:
            data = pickle.load(handle)

        cls._sparse_vectorizer = data["vectorizer"]
        cls._sparse_matrix = data["matrix"]
        cls._sparse_records = data["records"]

    @classmethod
    def ensure_ready(cls, db):
        try:
            cls._load_models()
            cls._load_qdrant()
            cls._load_sparse_index()
            cls._initialized = True
        except Exception:
            # First-use convenience: build the index automatically.
            cls.rebuild(db)

    @classmethod
    def _allowed_payload(cls, result, allowed_types: set[str]) -> bool:
        return bool(result.payload and result.payload.get("source_type") in allowed_types)

    @classmethod
    def _dense_search(cls, query: str, source_type: str, limit: int = 30) -> list[dict]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        vector = cls._embedder.encode(
            query,
            normalize_embeddings=True,
        ).tolist()

        client = cls._load_qdrant()
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value=source_type),
                )
            ]
        )

        try:
            results = client.search(
                collection_name=cls.COLLECTION,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        except AttributeError:
            results = client.query_points(
                collection_name=cls.COLLECTION,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            ).points

        output = []
        for rank, result in enumerate(results, start=1):
            payload = result.payload or {}
            output.append(
                {
                    "key": f"{source_type}:{payload.get('source_id')}",
                    "rank": rank,
                    "dense_score": float(result.score),
                    "payload": payload,
                }
            )
        return output

    @classmethod
    def _sparse_search(cls, query: str, source_type: str, limit: int = 30) -> list[dict]:
        q = cls._sparse_vectorizer.transform([query])
        scores = cosine_similarity(
            q,
            cls._sparse_matrix,
        )[0]

        candidates = []
        for index in np.argsort(scores)[::-1]:
            record = cls._sparse_records[index]
            if record["source_type"] != source_type:
                continue
            score = float(scores[index])
            if score <= 0:
                continue
            candidates.append(
                {
                    "key": f"{record['source_type']}:{record['source_id']}",
                    "rank": len(candidates) + 1,
                    "sparse_score": score,
                    "payload": record,
                }
            )
            if len(candidates) >= limit:
                break

        return candidates

    @classmethod
    def _fuse(cls, dense: list[dict], sparse: list[dict]) -> list[dict]:
        fused = {}

        for item in dense:
            row = fused.setdefault(item["key"], {"key": item["key"], "payload": item["payload"]})
            row["dense_score"] = item["dense_score"]
            row["rrf"] = row.get("rrf", 0.0) + 1.0 / (cls.RRF_K + item["rank"])

        for item in sparse:
            row = fused.setdefault(item["key"], {"key": item["key"], "payload": item["payload"]})
            row["sparse_score"] = item["sparse_score"]
            row["rrf"] = row.get("rrf", 0.0) + 1.0 / (cls.RRF_K + item["rank"])

        return sorted(
            fused.values(),
            key=lambda item: item["rrf"],
            reverse=True,
        )

    @classmethod
    def _rerank(cls, query: str, rows: list[dict], limit: int) -> list[dict]:
        shortlist = rows[: max(limit * 3, 12)]
        if not shortlist:
            return []

        pairs = [
            (
                query,
                row["payload"].get("text", ""),
            )
            for row in shortlist
        ]

        try:
            rerank_scores = cls._reranker.predict(pairs)
            ranked = []
            for row, score in zip(shortlist, rerank_scores):
                result = dict(row)
                raw_score = float(score)
                result["rerank_score"] = raw_score
                result["rerank_score_normalized"] = 1.0 / (1.0 + math.exp(-raw_score))
                ranked.append(result)
            ranked.sort(
                key=lambda item: item["rerank_score"],
                reverse=True,
            )
            return ranked[:limit]
        except Exception:
            # Retrieval remains functional if a reranker model is unavailable.
            for row in shortlist:
                row.setdefault("rerank_score_normalized", float(row.get("rrf", 0.0)))
            return shortlist[:limit]

    @classmethod
    def search(cls, query: str, source_types: set[str], limit: int = 5) -> list[dict]:
        # Each source gets its own dense+sparse candidate pool so one large corpus
        # cannot crowd out the other evidence classes.
        all_results = []
        for source_type in source_types:
            dense = cls._dense_search(query, source_type, limit=30)
            sparse = cls._sparse_search(query, source_type, limit=30)
            all_results.extend(
                cls._fuse(dense, sparse)
            )

        # Re-rank the combined evidence set while retaining source diversity.
        rows = cls._rerank(query, all_results, limit=max(limit * 3, 12))

        # Deduplicate by source, then return the requested top-N.
        seen = set()
        output = []
        for row in rows:
            if row["key"] in seen:
                continue
            seen.add(row["key"])
            output.append(row)
            if len(output) >= limit:
                break

        return output

    @classmethod
    def resolution_context(cls, ticket, db, ticket_limit=4, sop_limit=2, kb_limit=3) -> dict:
        cls.ensure_ready(db)

        query = cls._clean_text(
            f"{ticket.category or ''} {ticket.subcategory or ''} "
            f"{ticket.priority_level or ''} {ticket.business_impact or ''} "
            f"{ticket.summary or ''} {ticket.complaint_text or ''}"
        )

        ticket_rows = cls.search(query, {"ticket"}, limit=ticket_limit + 1)
        ticket_rows = [
            row
            for row in ticket_rows
            if str(row["payload"].get("ticket_id")) != str(ticket.id)
        ][:ticket_limit]

        sop_rows = cls.search(query, {"sop"}, limit=sop_limit)
        kb_rows = cls.search(query, {"kb"}, limit=kb_limit)

        def render(row: dict) -> dict:
            payload = row["payload"]
            return {
                "source_type": payload.get("source_type"),
                "source_id": payload.get("source_id"),
                "article_id": payload.get("article_id"),
                "ticket_id": payload.get("ticket_id"),
                "title": payload.get("title"),
                "status": payload.get("status"),
                "category": payload.get("category"),
                "subcategory": payload.get("subcategory"),
                "priority_level": payload.get("priority_level"),
                "assigned_agent_name": payload.get("assigned_agent_name"),
                "resolved_at": payload.get("resolved_at"),
                "summary": payload.get("summary"),
                "complaint_text": payload.get("complaint_text"),
                "content": payload.get("text", ""),
                "dense_score": round(float(row.get("dense_score", 0)), 4),
                "sparse_score": round(float(row.get("sparse_score", 0)), 4),
                "rrf_score": round(float(row.get("rrf", 0)), 6),
                "rerank_score": round(float(row.get("rerank_score", 0)), 4),
            }

        return {
            "method": "hybrid dense + TF-IDF sparse + RRF + cross-encoder reranking",
            "embedding_model": settings.EMBEDDING_MODEL,
            "reranker_model": settings.RERANKER_MODEL,
            "query": query,
            "tickets": [render(row) for row in ticket_rows],
            "sop": [render(row) for row in sop_rows],
            "kb": [render(row) for row in kb_rows],
        }
