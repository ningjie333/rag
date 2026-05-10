"""POST /api/query — RAG 检索问答"""
import structlog
from fastapi import APIRouter, Query

from models.schemas import QueryRequest, QueryResponse, Citation
from vector_store.query_engine import search_chunks, get_graph_context
from vector_store.kg_extractor import call_llm

router = APIRouter()
log = structlog.get_logger()

# RAG 生成提示词
RAG_SYSTEM = """你是一个专业的学科助教。基于检索到的教材内容和知识图谱上下文，准确回答学生问题。

要求：
1. 只基于提供的引用内容回答，不要编造
2. 如果引用内容不足以回答，明确说明
3. 回答要清晰、有条理，适当引用原文（用"【来源：页码】"标注）
4. 优先使用知识图谱中的关系路径来构建更完整的答案

回答格式：
[回答内容]
【来源：页码】"""

RAG_USER_TPL = """问题：{question}

参考内容：
{context}

{graph_section}
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

        # 3. 获取图谱上下文（GraphRAG）
        chunks_for_graph = [{"text": c.text} for c in citations]
        knowledge_paths, matched_entities = get_graph_context(req.question, chunks_for_graph)

        if knowledge_paths:
            graph_section = f"""知识图谱关系：
{chr(10).join(knowledge_paths)}

匹配的概念节点：{', '.join(matched_entities) if matched_entities else '无'}
"""
        else:
            graph_section = ""

        graph_context = {
            "knowledge_paths": knowledge_paths,
            "matched_entities": matched_entities,
        }

        # 4. 调用 LLM 生成回答
        user_prompt = RAG_USER_TPL.format(
            question=req.question,
            context=context,
            graph_section=graph_section,
        )
        answer = await call_llm(user_prompt, RAG_SYSTEM)

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
