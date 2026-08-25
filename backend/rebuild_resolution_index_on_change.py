from app.database.db import SessionLocal
from app.services.hybrid_retrieval_service import HybridRetrievalService


def main():
    db = SessionLocal()
    try:
        result = HybridRetrievalService.rebuild(db)
        print("=" * 60)
        print("RESOLUTION CONTEXT INDEX BUILT")
        print("=" * 60)
        for key, value in result.items():
            print(f"{key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
