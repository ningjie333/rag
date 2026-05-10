"""POST /api/query — RAG 检索问答"""
import structlog
from fastapi import APIRouter

from models.schemas import QueryRequest, QueryResponse, Citation

router = APIRouter()
log = structlog.get_logger()


@router.post("/query", response_model=QueryResponse)
async def query_question(req: QueryRequest):
    """
    接收问题，检索向量库，返回回答 + 引用来源。
    """
    log.info("query_request", question=req.question, top_k=req.top_k)

    # TODO: 后续由 DB-agent 接入 query_engine
    # 暂时返回占位响应
    return QueryResponse(
        answer=f"这是对「{req.question}」的回答（待接入向量库）",
        citations=[],
        graph_context={},
    )
