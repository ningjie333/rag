"""向量存储客户端

统一接口：ChromaDB → FAISS（解决 Python 3.14 兼容性问题）
"""
from .faiss_client import get_or_create_collection, reset_client, FAISSVectorStore

# 兼容性别名
get_client = get_or_create_collection

__all__ = ["get_or_create_collection", "reset_client", "get_client", "FAISSVectorStore"]