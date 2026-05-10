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
    """
    log.info("report_request", book_titles=book_titles)

    try:
        # 解析书籍列表
        titles = [t.strip() for t in book_titles.split(",") if t.strip()] if book_titles else None

        # 获取图谱数据
        all_graphs = get_full_graph()
        nodes = all_graphs.get("nodes", [])
        edges = all_graphs.get("edges", [])

        # 获取 chunks 统计
        collection = get_or_create_collection(settings.COLLECTION_CHUNKS)
        all_data = collection.get(include=["metadatas"])

        # 按书名聚合
        book_stats = {}
        for meta in all_data.get("metadatas", []):
            title = meta.get("book_title", "未知")
            if titles and title not in titles:
                continue
            if title not in book_stats:
                book_stats[title] = {"chunks": 0, "pages": set()}
            book_stats[title]["chunks"] += 1
            if meta.get("page"):
                book_stats[title]["pages"].add(meta["page"])

        # 构建报告
        report = f"""# 学科知识整合报告

生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 一、整合概况

| 指标 | 数值 |
|------|------|
| 整合教材数 | {len(book_stats)} |
| 总知识点数 | {len(nodes)} |
| 总关系数 | {len(edges)} |
| 压缩比 | {len(nodes) / sum(s['chunks'] for s in book_stats.values() or [1]) * 100:.1f}% |

## 二、各教材详情

"""
        for title, stats in book_stats.items():
            report += f"""### {title}

- 文本块数：{stats['chunks']}
- 页数范围：{min(stats['pages']) if stats['pages'] else 0} - {max(stats['pages']) if stats['pages'] else 0}

"""

        # 图谱节点分布
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

            # 关系类型分布
            rel_count = {}
            for edge in edges:
                rtype = edge.get("relation_type", "unknown")
                rel_count[rtype] = rel_count.get(rtype, 0) + 1

            report += "\n| 关系类型 | 数量 |\n|------|------|\n"
            for rtype, count in sorted(rel_count.items()):
                report += f"| {rtype} | {count} |\n"

        # 典型知识点案例
        if nodes:
            report += """
## 四、典型知识点（示例）

"""
            # 取置信度最高的 5 个
            top_nodes = sorted(nodes, key=lambda x: x.get("confidence", 0), reverse=True)[:5]
            for node in top_nodes:
                report += f"""### {node.get('label', '未知')}

- 类型：{node.get('type', 'unknown')}
- 描述：{node.get('description', '无描述')[:200]}
- 置信度：{node.get('confidence', 0):.2f}
- 来源：{node.get('source', '未知')}

"""

        report += f"""## 五、整合方法论

本报告通过以下步骤生成：
1. **PDF 解析**：使用 PyMuPDF 提取文本，过滤页眉页脚
2. **智能分块**：500 字/块，50 字重叠，保持语义完整性
3. **知识点提取**：LLM 驱动提取概念、定义、关系
4. **跨教材整合**：语义相似度 + LLM 推理去重合并
5. **图谱构建**：NetworkX 构建有向图，关系推理 + 去环

---
*本报告由学科知识整合智能体自动生成*
"""

        return {
            "success": True,
            "report": report,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "book_count": len(book_stats),
            }
        }

    except Exception as e:
        log.error("report_failed", error=str(e))
        return {
            "success": False,
            "report": f"# 报告生成失败\n\n错误：{str(e)}",
            "stats": {}
        }