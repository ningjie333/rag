"""POST /api/chat — 多轮对话"""
import structlog
from fastapi import APIRouter, Query

from models.schemas import ChatRequest, ChatResponse, ChatMessage, Citation
from vector_store.query_engine import search_chunks
from vector_store.kg_extractor import call_llm, get_full_graph

router = APIRouter()
log = structlog.get_logger()

# 多轮对话系统提示
CHAT_SYSTEM = """你是一个专业的学科助教，支持多轮对话。

特点：
1. 记忆上下文，能关联之前的讨论
2. 适当引用教材原文
3. 当用户要求整合或修改时，解释你的决策理由
4. 主动建议相关概念和学习路径

当前支持的教材：{book_titles}

如果用户讨论图谱整合，可以说"根据当前图谱，XX 和 YY 概念已被合并"。"""

CHAT_USER_TPL = """{history}

当前问题：{question}

请回答，如果涉及图谱概念可以引用：{graph_summary}"""


# 简单内存存储（生产环境用 Redis）
_conversation_history: dict[str, list[ChatMessage]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, session_id: str = Query(default="default")):
    """
    多轮对话，携带历史 messages + context。
    """
    log.info("chat_request", messages_count=len(req.messages), session_id=session_id)

    try:
        # 1. 获取/初始化对话历史
        history = _conversation_history.get(session_id, [])
        history.extend(req.messages)

        # 只保留最近 10 轮
        if len(history) > 20:
            history = history[-20:]

        # 2. 获取图谱上下文
        graph_data = get_full_graph()
        graph_nodes = graph_data.get("nodes", [])
        graph_summary = f"当前图谱有 {len(graph_nodes)} 个概念" if graph_nodes else "暂无图谱数据"

        # 3. 构建历史字符串
        history_str = ""
        for msg in history[-10:]:
            role = "用户" if msg.role == "user" else "助手"
            history_str += f"\n{role}：{msg.content}"

        # 4. 检索相关 chunks
        last_question = req.messages[-1].content if req.messages else ""
        citations = search_chunks(last_question, top_k=3)

        # 5. 构建上下文
        context_parts = []
        for c in citations:
            context_parts.append(f"【来源：{c.source} 第{c.page}页】\n{c.text}\n")
        context = "\n---\n".join(context_parts) if context_parts else "（无可用引用）"

        # 6. 构建 prompt
        system_prompt = CHAT_SYSTEM.format(
            book_titles=", ".join(req.context.book_titles) if req.context.book_titles else "未知"
        )
        user_prompt = CHAT_USER_TPL.format(
            history=history_str,
            question=last_question,
            graph_summary=graph_summary,
        )
        user_prompt += f"\n\n参考内容：\n{context}"

        # 7. 调用 LLM
        answer = await call_llm(user_prompt, system_prompt)

        # 8. 保存历史
        history.append(ChatMessage(role="user", content=last_question))
        history.append(ChatMessage(role="assistant", content=answer))
        _conversation_history[session_id] = history

        # 9. 返回
        return ChatResponse(
            reply=answer,
            citations=citations,
            graph_snapshot={"node_count": len(graph_nodes)},
        )

    except Exception as e:
        log.error("chat_failed", error=str(e))
        return ChatResponse(
            reply=f"抱歉，对话出现错误：{str(e)}",
            citations=[],
            graph_snapshot={},
        )


@router.delete("/chat")
async def clear_chat(session_id: str = Query(default="default")):
    """清除对话历史"""
    if session_id in _conversation_history:
        del _conversation_history[session_id]
    return {"success": True, "message": f"会话 {session_id} 已清除"}
