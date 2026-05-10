"""POST /api/chat — 多轮对话"""
import structlog
from fastapi import APIRouter

from models.schemas import ChatRequest, ChatResponse, Citation

router = APIRouter()
log = structlog.get_logger()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    多轮对话，携带历史 messages + context。
    """
    log.info("chat_request", messages_count=len(req.messages))

    # TODO: 接入 RAG + 图谱上下文
    last_msg = req.messages[-1].content if req.messages else ""
    return ChatResponse(
        reply=f"你说的是「{last_msg}」，这是多轮对话回复（待接入）",
        citations=[],
        graph_snapshot={},
    )
