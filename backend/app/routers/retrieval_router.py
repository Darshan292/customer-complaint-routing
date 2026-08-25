from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.hybrid_retrieval_service import HybridRetrievalService

router = APIRouter(tags=["Retrieval"])


@router.get("/retrieval/status")
def retrieval_status():
    return {
        "index": HybridRetrievalService.COLLECTION,
        "method": "dense + TF-IDF sparse + RRF + cross-encoder reranking",
        "embedding_model": "configured",
        "reranker_model": "configured",
    }


@router.post("/retrieval/rebuild-index")
def rebuild_resolution_index(db: Session = Depends(get_db)):
    try:
        return HybridRetrievalService.rebuild(db)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Resolution retrieval index rebuild failed: {exc}",
        )
