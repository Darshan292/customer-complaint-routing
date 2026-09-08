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

    # Temporary Workday Cost Center EIB workflow. Keep credentials in
    # Codespaces environment secrets; never commit them to source control.
    #WD_DEFAULT_ENDPOINT: str = ""
    #WD_DEFAULT_USERNAME: str = ""
    #WD_DEFAULT_PASSWORD: str = ""
    WD_DEFAULT_ENDPOINT:str = "https://impl-services1.wd12.myworkday.com/ccx/service/tcs_dpt2/Integrations/v47.0"             
    WD_DEFAULT_USERNAME:str  = "UYoga@tcs_dpt2"
    WD_DEFAULT_PASSWORD:str  = "Workday@12345"

    WD_COST_CENTER_INTEGRATION_ID: str = "InboundEIBCreateCostCenter"
    WD_COST_CENTER_AGENT_ID: int = 2

    DATABASE_URL: str = (
        f"sqlite:///{BASE_DIR / 'complaints.db'}"
    )

    class Config:
        env_file = ".env"


settings = Settings()