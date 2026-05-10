"""POST /api/query — RAG 检索问答"""
import structlog
from fastapi import APIRouter, Query

from models.schemas import QueryRequest, QueryResponse, Citation
from vector_store.query_engine import search_chunks
from vector_store.kg_extractor import call_minimax

router = APIRouter()
log = structlog.get_logger()

# RAG 生成提示词
RAG_SYSTEM = """你是一个专业的学科助教。基于检索到的教材内容，准确回答学生问题。

要求：
1. 只基于提供的引用内容回答，不要编造
2. 如果引用内容不足以回答，明确说明
3. 回答要清晰、有条理
4. 适当引用原文（用"【来源：页码】"标注）

回答格式：
[回答内容]
【来源：页码】"""

RAG_USER_TPL = """问题：{question}

参考内容：
{context}

请基于以上内容回答问题。"""


@router.post("/query", response_model=QueryResponse)
async def query_question(req: QueryRequest, book_title: str = Query(None)):
    """
    接收问题，检索向量库，返回回答 + 引用来源。
    """
    log.info("query_request", question=req.question, top_k=req.top_k, book_title=book_title)

    try:
        # 1. 检索相关 chunks
        citations = search_chunks(req.question, req.top_k, book_title)

        if not citations:
            return QueryResponse(
                answer="抱歉，我在知识库中没有找到与您问题相关的内容。请尝试换一种问法或上传更多教材。",
                citations=[],
                graph_context={},
            )

        # 2. 构建上下文
        context_parts = []
        for c in citations:
            context_parts.append(f"【来源：{c.source} 第{c.page}页】\n{c.text}\n")

        context = "\n---\n".join(context_parts)

        # 3. 调用 LLM 生成回答
        user_prompt = RAG_USER_TPL.format(question=req.question, context=context)
        answer = await call_minimax(user_prompt, RAG_SYSTEM)

        # 4. 获取图谱上下文（如果有相关节点）
        graph_context = {}
        # TODO: 后续接入图谱查询

        return QueryResponse(
            answer=answer,
            citations=citations,
            graph_context=graph_context,
        )

    except Exception as e:
        log.error("query_failed", error=str(e))
        return QueryResponse(
            answer=f"抱歉，回答时出现错误：{str(e)}",
            citations=[],
            graph_context={},
        )
