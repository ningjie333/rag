"""应用配置"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 加载项目根目录的 .env (scaffold 目录下)
load_dotenv(BASE_DIR / ".env")

# 数据目录（优先用环境变量，支持 Docker / Railway / 本地）
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
CHROMA_DIR = Path(os.environ.get("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma_db")))
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    # LLM Provider: openai, minimax
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.longcat.chat/openai")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "LongCat-2.0-Preview")

    # MiniMax (fallback)
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_BASE_URL: str = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
    MINIMAX_MODEL: str = os.getenv("MINIMAX_MODEL", "MiniMax-Text-01")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 3002

    # Paths
    CHROMA_PERSIST_DIR: str = str(CHROMA_DIR)

    # CORS - 支持 Vercel 前端
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "https://rag-smoky.vercel.app",
    ]

    # Vector store
    COLLECTION_CHUNKS: str = "textbook_chunks"
    COLLECTION_KG: str = "knowledge_graph"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5

    # Data directories
    DATA_DIR: str = str(DATA_DIR)

    class Config:
        env_file = ".env"

settings = Settings()
