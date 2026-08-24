from pathlib import Path

from pydantic_settings import BaseSettings


BASE_DIR = Path(
    __file__
).resolve().parents[2]


class Settings(BaseSettings):

    GROQ_API_KEY: str

    MODEL_NAME: str

    DATABASE_URL: str = (
        f"sqlite:///{BASE_DIR / 'complaints.db'}"
    )

    class Config:
        env_file = ".env"


settings = Settings()