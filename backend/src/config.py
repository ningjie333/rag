from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Model names
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Paths
    VECTOR_STORE_DIR: Path = Path(__file__).parent.parent / "vector_store"
    DATA_DIR: Path = Path(__file__).parent.parent / "data"

    # RAG settings
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 80
    TOP_K: int = 5

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()