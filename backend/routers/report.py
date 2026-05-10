"""GET /api/report — 整合报告生成"""
import structlog
from fastapi import APIRouter, Query
from datetime import datetime

from vector_store.kg_extractor import get_full_graph
from vector_store.chroma_client import get_or_create_collection
from config import settings

router = APIRouter()
log = structlog.get_logger()


@router.get("/report")
async def generate_report(book_titles: str = Query(None, description="逗号分隔的书籍标题，空表示全部")):
    """
    生成教材整合报告。
    从真实向量库读取 chunks 和知识图谱数据统计。
    """
    log.info("report_request", book_titles=book_titles)

    try:
        titles = [t.strip() for t in book_titles.split(",") if t.strip()] if book_titles else None

        chunks_col = get_or_create_collection(settings.COLLECTION_CHUNKS)
        chunks_count = chunks_col.count()
        all_chunks = chunks_col.get(include=["metadatas"])

        book_titles_set = set()
        book_stats = {}
        for meta in all_chunks.get("metadatas", []):
            if not meta:
                continue
            title = meta.get("book_title", "未知")
            if titles and title not in titles:
                continue
            book_titles_set.add(title)
            if title not in book_stats:
                book_stats[title] = {"chunks": 0, "pages": set()}
            book_stats[title]["chunks"] += 1
            if meta.get("page"):
                book_stats[title]["pages"].add(meta["page"])

        kg_col = get_or_create_collection(settings.COLLECTION_KG)
        kg_nodes_data = kg_col.get(where={"type": "node"}, include=["metadatas"])
        kg_edges_data = kg_col.get(where={"type": "edge"}, include=["metadatas"])

        nodes = []
        for meta in kg_nodes_data.get("metadatas", []):
            if meta and meta.get("data"):
                import json
                try:
                    nodes.append(json.loads(meta["data"]))
                except (json.JSONDecodeError, TypeError):
                    pass

        edges = []
        for meta in kg_edges_data.get("metadatas", []):
            if meta and meta.get("data"):
                import json
                try:
                    edges.append(json.loads(meta["data"]))
                except (json.JSONDecodeError, TypeError):
                    pass

        total_chunks = sum(s["chunks"] for s in book_stats.values()) if book_stats else 0
        compression_ratio = f"{len(nodes) / total_chunks * 100:.1f}" if total_chunks > 0 else "N/A"

        report = f"""# 学科知识整合报告

生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 一、整合概况

| 指标 | 数值 |
|------|------|
| 整合教材数 | {len(book_stats)} |
| 文本分块总数 | {total_chunks} |
| 知识节点总数 | {len(nodes)} |
| 关系边总数 | {len(edges)} |
| 压缩比 | {compression_ratio}% |

## 二、各教材详情

"""
        for title, stats in book_stats.items():
            pages = stats["pages"]
            report += f"""### {title}

- 文本块数：{stats['chunks']}
- 页数范围：{min(pages) if pages else 0} - {max(pages) if pages else 0}

"""

        if nodes:
            report += """## 三、知识图谱结构

"""
            type_count = {}
            for node in nodes:
                ntype = node.get("type", "unknown")
                type_count[ntype] = type_count.get(ntype, 0) + 1

            report += "| 节点类型 | 数量 |\n|------|------|\n"
            for ntype, count in sorted(type_count.items()):
                report += f"| {ntype} | {count} |\n"

            rel_count = {}
            for edge in edges:
                rtype = edge.get("relation_type", "unknown")
                rel_count[rtype] = rel_count.get(rtype, 0) + 1

            report += "\n| 关系类型 | 数量 |\n|------|------|\n"
            for rtype, count in sorted(rel_count.items()):
                report += f"| {rtype} | {count} |\n"

        if nodes:
            report += """
## 四、典型知识点

"""
            top_nodes = sorted(nodes, key=lambda x: x.get("confidence", 0), reverse=True)[:5]
            for node in top_nodes:
                report += f"""### {node.get('label', node.get('name', '未知'))}

- 类型：{node.get('type', node.get('category', 'unknown'))}
- 描述：{node.get('description', '无描述')[:200]}
- 置信度：{node.get('confidence', 0):.2f}
- 来源：{node.get('source', '未知')}

"""

        report += """## 五、整合方法论

本报告通过以下步骤生成：
1. **PDF 解析**：使用 PyMuPDF 提取文本，过滤页眉页脚
2. **智能分块**：500 字/块，50 字重叠，保持语义完整性
3. **知识点提取**：LLM 驱动提取概念、定义、关系
4. **跨教材整合**：语义相似度 + LLM 推理去重合并
5. **图谱构建**：FAISS 向量存储，关系推理 + 去环

---
*本报告由学科知识整合智能体自动生成*
"""

        return {
            "success": True,
            "report": report,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "total_chunks": total_chunks,
                "book_count": len(book_stats),
                "compression_ratio": compression_ratio,
            }
        }

    except Exception as e:
        log.error("report_failed", error=str(e))
        return {
            "success": False,
            "report": f"# 报告生成失败\n\n无法生成整合报告。\n\n**错误原因：** {str(e)}\n\n**建议：**\n1. 确认已上传教材并完成知识图谱构建\n2. 检查后端服务是否正常启动\n3. 查看后端日志获取详细信息",
            "stats": {}
        }