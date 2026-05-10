"""GET /api/books — 书籍列表"""
import structlog
from fastapi import APIRouter

from models.schemas import BooksResponse, BookInfo

router = APIRouter()
log = structlog.get_logger()


@router.get("/books", response_model=BooksResponse)
async def list_books():
    """
    返回已上传的教材列表。
    """
    log.info("books_request")
    # TODO: 从 ChromaDB 元数据查询已上传书籍
    return BooksResponse(books=[])
