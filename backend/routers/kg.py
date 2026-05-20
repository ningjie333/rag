"""GET /api/graph — 知识图谱查询 & 构建"""
import asyncio
import json
import structlog
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from models.schemas import GraphResponse, KGNode, KGEdge
from vector_store.kg_extractor import extract_knowledge_graph, extract_knowledge_graph_batch, store_knowledge_graph, get_full_graph
from vector_store.relation_inferrer import infer_all_relations, remove_cycles, merge_duplicate_concepts, dual_align_concepts
from vector_store.chroma_client import get_or_create_collection
from config import settings, BASE_DIR

router = APIRouter()
log = structlog.get_logger()

# 已有的离线图谱 JSON 文件目录
EXPORT_INDIVIDUAL_DIR = BASE_DIR / "export_output" / "individual"


# Known non-medical noise terms from PDF front matter
NOISE_TERMS = {
    # Awards & honors
    "科学进步奖", "教学成果奖", "一等奖", "二等奖", "优秀奖", "获奖",
    # Publishing staff (编委会页)
    "编委", "主编", "副主编", "审定", "批准", "编写说明", "前言", "序言",
    "出版说明", "编辑说明", "声明", "版权所有", "版权信息", "版权页",
    "编者", "编委名单", "编著", "编写", "主编寄语",
    # Administrative/pedagogical terms (教材前言/编委会混入)
    "教材建设", "教材精品", "教材提质", "教材管理", "规划教材", "教材办法",
    "课程思政", "教育数字化", "数字资源", "数字人", "三维模型", "思维导图",
    "电子教材", "纸数融合", "新形态教材", "套色线条图",
    "立德树人", "守正创新", "医者精神", "三基", "五性", "三特定", "两性一度",
    "医德医风", "数字内容", "医学教育",
    # Book/meeting names that are administrative
    "干细胞教材", "首届全国教材工作会议", "临床医学专业教材评审", "教材工作会议",
    "党的教育方针", "医学教育改革发展", "深化医教协同", "加快医学教育创新",
    "高校思想政治工作", "全国高校思想政治工作会议",
    # Common textbook administrative terms across all books
    "五年制本科", "本科教育", "教学工作", "教育工作", "核心教材",
    "形态教材", "纸质教材", "在线课程", "重点人群", "健康教育", "性卫生教育",
    "教材体系", "患沟通", "教育部", "变革的思维", "探索教育", "教材",
    # Political/governance terms
    "新时代中国特色社会主义", "习近平", "马克思主义", "社会主义", "共产主义",
    "帝国主义", "资本主义", "封建主义", "民族主义", "民粹主义",
    "恐怖主义",
    # Administrative awards & programs (人才/工程/进步/计划 + award-like combos)
    "科技进步奖", "科学技术进步奖", "教学成果奖", "优秀人才", "人才工程", "人才支持计划",
    "科技新星计划", "百千万人才", "基金委员会", "自然科学基金", "重大研究计划", "重大研究专项", "重点基金", "科技部",
    # Glossary/index terms
    "名词", "中英文对照", "索引",
    # Administrative/legal/governance terms
    "中华优秀传统文化", "生物安全法", "法定计量单位", "中华人民共和国",
    # Generic standalone noise terms
    "计划", "工程",
    # Known person names from book front matter (编委会)
    "钱亦华", "张卫光", "张雅芳", "丁强", "武艳", "王启明", "欧阳钧",
    # Non-medical methodology/admin terms
    "周围区", "高热", "观察", "外科学", "妇产科学", "结构观察", "解剖器械", "自主学习", "人体分部", "解剖刀",
    # Abbreviations that are too generic in medical context
    "DICOM", "PET", "CT",
}

def _is_noise_node(label: str) -> bool:
    """Check if a node label is a known non-medical noise term."""
    if not label:
        return True
    for term in NOISE_TERMS:
        if term in label:
            return True
    return False


def _load_graph_from_json_files(book_title: str | None = None) -> dict:
    """
    从 export_output/individual/*.json 读取图谱数据作为后备。
    合并所有有效的 individual JSON 文件（有节点且节点数 > 0 的）。

    节点 ID 统一为短格式：{书名}_{概念名[:20]}
    边引用同步更新为新 ID，以正确连接节点。
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    scan_dir = EXPORT_INDIVIDUAL_DIR

    if not scan_dir.is_dir():
        log.warning("export_output individual dir not found", path=str(scan_dir))
        return {"nodes": [], "edges": []}

    json_files = list(scan_dir.glob("*_知识图谱.json"))
    log.info("loading_graph_from_json", file_count=len(json_files), book_title=book_title)

    for json_file in json_files:
        # 从文件名提取书名，如 "01_局部解剖学_知识图谱.json" → "01_局部解剖学"
        file_stem = json_file.stem.replace("_知识图谱", "")
        if book_title and file_stem != book_title:
            continue

        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            file_nodes = data.get("nodes", [])
            file_edges = data.get("edges", [])

            # 跳过 0 节点的失败文件（如 05/07 扫描版 PDF）
            if not file_nodes:
                log.info("skipping_empty_json", file=str(json_file))
                continue

            # 记录旧 ID → 新 ID 的映射（同一个概念跨文件取第一个）
            old_to_new: dict[str, str] = {}
            for n in file_nodes:
                old_id = n.get("id", "")
                n_name = n.get("name") or n.get("label", "")
                safe_id = f"{file_stem}_{n_name[:20]}"
                n["id"] = safe_id
                if old_id and old_id not in old_to_new:
                    old_to_new[old_id] = safe_id

            # 更新边引用
            for e in file_edges:
                old_from = e.get("from", "")
                old_to = e.get("to", "")
                e["from"] = old_to_new.get(old_from, old_from)
                e["to"] = old_to_new.get(old_to, old_to)

            nodes.extend(file_nodes)
            edges.extend(file_edges)
            log.info("loaded_json_file", file=str(json_file), nodes=len(file_nodes), edges=len(file_edges))
        except Exception as e:
            log.warning("failed_to_load_json", file=str(json_file), error=str(e))
            continue

    # 过滤噪声节点（出版信息、奖项等非医学内容）
    before_nodes = len(nodes)
    nodes = [n for n in nodes if not _is_noise_node(n.get("name") or n.get("label", ""))]
    removed_noise = before_nodes - len(nodes)
    log.info("filtered_noise_nodes", removed=removed_noise)

    # 过滤无效边（引用了不存在节点的边）
    node_ids = {n["id"] for n in nodes}
    before_edges = len(edges)
    edges = [e for e in edges if e.get("from") in node_ids and e.get("to") in node_ids]
    log.info("filtered_invalid_edges", before=before_edges, after=len(edges), removed=before_edges - len(edges))

    log.info("graph_from_json_total", nodes=len(nodes), edges=len(edges))
    return {"nodes": nodes, "edges": edges}


@router.get("/graph", response_model=GraphResponse)
async def get_graph(book_title: Optional[str] = Query(None)):
    """
    返回知识图谱的 nodes + edges。
    book_title 为空则返回所有。

    优先从 FAISS 存储读取；若 FAISS 为空则 fallback 到 export_output JSON 文件。
    全量 27000+ 节点前端渲染困难，空参数时默认加载"01_局部解剖学"。
    """
    # 全量数据太大，默认只加载一本书
    if not book_title:
        book_title = "01_局部解剖学"
        log.info("no_book_title_defaulting", default=book_title)
    log.info("graph_request", book_title=book_title)

    try:
        # 先尝试从 FAISS 存储读取
        graph_data = get_full_graph(book_title)

        # FAISS 为空或无有效边时 fallback 到已有 JSON 文件
        # mock 数据有 0 条边，而真实数据 edges > 0
        if not graph_data.get("nodes") or len(graph_data.get("edges", [])) == 0:
            log.info("faiss_empty_using_json_fallback", faiss_nodes=len(graph_data.get("nodes", [])), faiss_edges=len(graph_data.get("edges", [])))
            graph_data = _load_graph_from_json_files(book_title)

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
        # 转换 edges：JSON 文件用 from/to，schema 用 from_node/to_node
        raw_edges = graph_data.get("edges", [])
        edges = []
        for e in raw_edges:
            edges.append(KGEdge(
                from_node=e.get("from", e.get("from_node", "")),
                to_node=e.get("to", e.get("to_node", "")),
                relation_type=e.get("relation_type", "associate"),
                weight=e.get("weight", 0.8),
            ))

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

        # 1. 并行提取知识点（多 agent 架构）
        all_nodes, all_edges = await extract_knowledge_graph_batch(
            chunks,
            book_title,
            max_concurrency=5,
        )

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


@router.post("/graph/build-all")
async def build_all_graphs(
    max_concurrent_books: int = Query(3, description="最多同时处理几本教材"),
    target_ratio: float = Query(0.3, description="跨教材压缩比"),
):
    """
    多 agent 并行架构：同时构建所有教材的知识图谱。

    1. 获取所有教材列表
    2. 并行触发每本教材的图谱构建（最多 max_concurrent_books 本同时）
    3. 等待所有教材完成
    4. 跨教材合并 + 压缩
    """
    log.info("build_all_request", max_concurrent_books=max_concurrent_books)

    try:
        # 获取所有教材
        collection = get_or_create_collection("textbook_chunks")
        results = collection.get(include=["documents", "metadatas"])

        if not results or not results.get("documents"):
            raise HTTPException(status_code=404, detail="没有找到任何教材")

        # 按 book_title 分组
        book_chunks: dict[str, list] = {}
        for doc, meta in zip(results["documents"], results["metadatas"]):
            title = meta.get("book_title", "unknown")
            if title not in book_chunks:
                book_chunks[title] = []
            book_chunks[title].append({
                "text": doc,
                "metadata": meta,
            })

        log.info("books_discovered", book_count=len(book_chunks), books=list(book_chunks.keys()))

        # 并行构建每本教材的图谱
        semaphore = asyncio.Semaphore(max_concurrent_books)

        async def build_single_book(title: str, chunks: list) -> dict:
            async with semaphore:
                log.info("building_single_book", book=title, chunks=len(chunks))
                nodes, edges = await extract_knowledge_graph_batch(
                    chunks, title, max_concurrency=5
                )
                # 合并重复
                merged = merge_duplicate_concepts(nodes)
                # 推理关系
                relations = await infer_all_relations(merged)
                relations = remove_cycles(relations, merged)
                # 存储
                kg_data = {"nodes": merged, "edges": relations}
                store_knowledge_graph(kg_data, title)
                log.info("book_done", book=title, nodes=len(merged), edges=len(relations))
                return {
                    "book": title,
                    "chunks": len(chunks),
                    "nodes": len(merged),
                    "edges": len(relations),
                }

        # 创建所有任务
        tasks = [
            build_single_book(title, chunks)
            for title, chunks in book_chunks.items()
        ]

        # 并行执行
        book_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计成功/失败
        successful = []
        failed = []
        for i, result in enumerate(book_results):
            title = list(book_chunks.keys())[i]
            if isinstance(result, Exception):
                failed.append({"book": title, "error": str(result)})
            else:
                successful.append(result)

        log.info("all_books_done", successful=len(successful), failed=len(failed))

        # 跨教材合并 + 压缩
        all_graphs = get_full_graph()
        all_nodes = all_graphs.get("nodes", [])
        all_edges = all_graphs.get("edges", [])

        merged_nodes = merge_duplicate_concepts(all_nodes)
        original_count = len(all_nodes)
        merged_count = len(merged_nodes)

        # 按压缩比裁剪
        target_count = int(original_count * target_ratio) if original_count > 0 else 0
        if merged_count > target_count:
            merged_nodes.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            merged_nodes = merged_nodes[:target_count]

        node_ids = {n.get("id") for n in merged_nodes}
        all_edges = [e for e in all_edges if e.get("from") in node_ids and e.get("to") in node_ids]
        all_edges = remove_cycles(all_edges, merged_nodes)

        merged_graph = {"nodes": merged_nodes, "edges": all_edges}
        store_knowledge_graph(merged_graph, "_merged_")

        return {
            "success": True,
            "message": f"全部完成，成功 {len(successful)} 本，失败 {len(failed)} 本",
            "books": successful,
            "failed_books": failed,
            "merged_graph": {
                "total_nodes": len(merged_nodes),
                "total_edges": len(all_edges),
                "compression_ratio": round(merged_count / original_count, 2) if original_count else 1.0,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error("build_all_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"全量构建失败: {str(e)}")
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
