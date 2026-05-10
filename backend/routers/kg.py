"""GET /api/graph — 知识图谱查询 & 构建"""
import structlog
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from models.schemas import GraphResponse, KGNode, KGEdge
from vector_store.kg_extractor import extract_knowledge_graph, store_knowledge_graph, get_full_graph
from vector_store.relation_inferrer import infer_all_relations, remove_cycles, merge_duplicate_concepts, dual_align_concepts
from vector_store.chroma_client import get_or_create_collection

router = APIRouter()
log = structlog.get_logger()


@router.get("/graph", response_model=GraphResponse)
async def get_graph(book_title: Optional[str] = Query(None)):
    """
    返回知识图谱的 nodes + edges。
    book_title 为空则返回所有。
    """
    log.info("graph_request", book_title=book_title)

    try:
        graph_data = get_full_graph(book_title)
        # 转换节点格式以匹配 KGNode schema
        raw_nodes = graph_data.get("nodes", [])
        nodes = []
        for n in raw_nodes:
            nodes.append({
                "id": n.get("id", ""),
                "label": n.get("label", n.get("name", "")),
                "type": n.get("category", "concept"),
                "description": n.get("definition", n.get("description", "")),
                "source": n.get("source", book_title or ""),
            })
        edges = [KGEdge(**e) for e in graph_data.get("edges", [])]

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )
    except Exception as e:
        log.error("get_graph_failed", error=str(e))
        return GraphResponse(
            nodes=[],
            edges=[],
            total_nodes=0,
            total_edges=0,
        )


@router.post("/graph/build")
async def build_graph(book_title: str = Query(..., description="教材标题")):
    """
    触发知识图谱构建（从已上传的教材提取知识点）。

    流程：
    1. 从 ChromaDB 获取该教材的所有 chunks
    2. 对每个 chunk 调用 LLM 提取知识点
    3. 合并重复概念
    4. 推理概念间关系
    5. 存储到 KG collection
    """
    log.info("graph_build_request", book_title=book_title)

    try:
        # 从 ChromaDB 获取该教材的 chunks
        collection = get_or_create_collection("textbook_chunks")
        results = collection.get(
            where={"book_title": book_title} if book_title else None,
            include=["documents", "metadatas"],
        )

        if not results or not results.get("documents"):
            raise HTTPException(status_code=404, detail=f"教材 '{book_title}' 未找到或无内容")

        chunks = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            chunks.append({
                "text": doc,
                "metadata": meta,
            })

        log.info("building_graph", chunk_count=len(chunks))

        # 1. 提取知识点
        all_nodes = []
        all_edges = []
        for chunk in chunks:
            kg_data = await extract_knowledge_graph(
                chunk["text"],
                source=chunk["metadata"].get("source", book_title),
            )
            # 给节点添加 source
            for node in kg_data.get("nodes", []):
                node["source"] = book_title
            all_nodes.extend(kg_data.get("nodes", []))
            all_edges.extend(kg_data.get("edges", []))

        log.info("extraction_done", node_count=len(all_nodes), edge_count=len(all_edges))

        # 2. 合并重复概念
        merged_nodes = merge_duplicate_concepts(all_nodes)
        log.info("merge_done", after_count=len(merged_nodes))

        # 3. 推理关系
        relations = await infer_all_relations(merged_nodes)
        log.info("relation_inference_done", relation_count=len(relations))

        # 4. 去环
        relations = remove_cycles(relations, merged_nodes)

        # 5. 存储
        kg_data = {
            "nodes": merged_nodes,
            "edges": relations,
        }
        store_knowledge_graph(kg_data, book_title)

        return {
            "success": True,
            "message": f"图谱构建完成",
            "stats": {
                "original_nodes": len(all_nodes),
                "merged_nodes": len(merged_nodes),
                "relations": len(relations),
                "compression_ratio": len(merged_nodes) / len(all_nodes) if all_nodes else 1.0,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error("graph_build_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"图谱构建失败: {str(e)}")


@router.post("/graph/merge")
async def merge_graphs(target_ratio: float = Query(0.3, description="目标压缩比")):
    """
    跨教材整合 + 压缩到目标比例（默认 30%）。

    流程：
    1. 获取所有教材的图谱
    2. 跨教材去重合并
    3. 按压缩比裁剪低置信度节点
    """
    log.info("graph_merge_request", target_ratio=target_ratio)

    try:
        # 获取所有图谱
        all_graphs = get_full_graph()
        nodes = all_graphs.get("nodes", [])
        edges = all_graphs.get("edges", [])

        if not nodes:
            return {"success": True, "ratio": 1.0, "message": "无图谱数据"}

        # 跨教材去重
        merged_nodes = merge_duplicate_concepts(nodes)
        original_count = len(nodes)
        merged_count = len(merged_nodes)

        # 按置信度排序，裁剪到目标比例
        target_count = int(original_count * target_ratio)
        if merged_count > target_count:
            merged_nodes.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            merged_nodes = merged_nodes[:target_count]

        # 移除孤立边
        node_ids = {n.get("id") for n in merged_nodes}
        edges = [e for e in edges if e.get("from") in node_ids and e.get("to") in node_ids]

        # 去环
        edges = remove_cycles(edges, merged_nodes)

        # 存储合并后的图谱
        merged_graph = {"nodes": merged_nodes, "edges": edges}
        store_knowledge_graph(merged_graph, "_merged_")

        achieved_ratio = merged_count / original_count if original_count else 1.0

        dual_alignment = {"surface_matches": 0, "semantic_matches": 0, "total_aligned": 0, "examples": []}
        try:
            align_result = dual_align_concepts(nodes)
            surface_count = len(align_result["surface_matches"])
            semantic_count = len(align_result["semantic_matches"])
            dual_alignment = {
                "surface_matches": surface_count,
                "semantic_matches": semantic_count,
                "total_aligned": align_result["total_aligned"],
                "examples": (
                    align_result["surface_matches"][:3] + align_result["semantic_matches"][:2]
                )[:5],
            }
        except Exception as align_err:
            log.warning("dual_align_failed", error=str(align_err))

        compression_detail = {
            "before": original_count,
            "after_dedup": merged_count,
            "after_alignment": max(merged_count - dual_alignment["total_aligned"], 1),
            "surface_ratio": round(merged_count / original_count, 2) if original_count else 1.0,
            "semantic_ratio": round(
                max(merged_count - dual_alignment["total_aligned"], 1) / original_count, 2
            )
            if original_count
            else 1.0,
        }

        return {
            "success": True,
            "ratio": achieved_ratio,
            "message": f"整合完成，{original_count} → {merged_count} 节点",
            "stats": {
                "original_nodes": original_count,
                "merged_nodes": merged_count,
                "target_ratio": target_ratio,
                "achieved_ratio": achieved_ratio,
                "edges": len(edges),
            },
            "dual_alignment": dual_alignment,
            "compression_detail": compression_detail,
        }

    except Exception as e:
        log.error("graph_merge_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"图谱整合失败: {str(e)}")
