from pathlib import Path

from pydantic_settings import BaseSettings


BASE_DIR = Path(
    __file__
).resolve().parents[2]


class Settings(BaseSettings):

    GROQ_API_KEY: str

    MODEL_NAME: str

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    VECTOR_STORE_PATH: str = str(BASE_DIR / "vector_store")
    KNOWLEDGE_DIR: str = str(BASE_DIR / "data/knowledge")
    SOP_PATH: str = str(BASE_DIR / "data/knowledge/sop_enterprise.txt")
    KB_PATH: str = str(BASE_DIR / "data/knowledge/kb_enterprise.txt")

    DATABASE_URL: str = (
        f"sqlite:///{BASE_DIR / 'complaints.db'}"
    )

    class Config:
        env_file = ".env"


settings = Settings()