"""GET /api/books — 书籍列表"""
import structlog
from fastapi import APIRouter

from models.schemas import BooksResponse, BookInfo
from vector_store.chroma_client import get_or_create_collection
from config import settings

router = APIRouter()
log = structlog.get_logger()


@router.get("/books", response_model=BooksResponse)
async def list_books():
    """
    返回已上传的教材列表。
    从 ChromaDB 元数据聚合已上传书籍。
    """
    log.info("books_request")

    try:
        collection = get_or_create_collection(settings.COLLECTION_CHUNKS)

        # 获取所有 chunks 的 metadata
        all_data = collection.get(include=["metadatas"])

        # 聚合不同 book_title
        book_stats = {}
        for meta in all_data.get("metadatas", []):
            title = meta.get("book_title", "未知")
            if title not in book_stats:
                book_stats[title] = {
                    "title": title,
                    "chunk_count": 0,
                    "created_at": "2024-01-01",  # TODO: 记录实际时间
                }
            book_stats[title]["chunk_count"] += 1

        books = list(book_stats.values())
        return BooksResponse(books=books)

    except Exception as e:
        log.error("list_books_failed", error=str(e))
        return BooksResponse(books=[])
