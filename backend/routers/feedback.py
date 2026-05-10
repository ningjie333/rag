"""POST /api/feedback — 反馈处理接口"""
import json
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from vector_store.kg_extractor import get_full_graph, store_knowledge_graph
from vector_store.chroma_client import get_or_create_collection
from config import settings

router = APIRouter()
log = structlog.get_logger()


class FeedbackRequest(BaseModel):
    feedback_type: str  # correct_relation | incorrect_relation | update_node | new_relation
    node_id: Optional[str] = None
    relation_from: Optional[str] = None
    relation_to: Optional[str] = None
    content: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """
    处理用户反馈，更新知识图谱。

    支持 4 种反馈类型：
    - correct_relation: 确认关系正确 → weight = min(1.0, weight * 1.2)
    - incorrect_relation: 关系错误 → weight *= 0.5
    - update_node: 更新节点 description
    - new_relation: 添加新关系
    """
    log.info("feedback_received", feedback_type=req.feedback_type, node_id=req.node_id)

    try:
        graph_data = get_full_graph()
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        updated = {}

        if req.feedback_type == "correct_relation":
            # 确认关系正确 → weight = min(1.0, weight * 1.2)
            for edge in edges:
                if (req.relation_from and req.relation_to
                        and edge.get("from") == req.relation_from
                        and edge.get("to") == req.relation_to):
                    old_weight = edge.get("weight", 0.5)
                    edge["weight"] = min(1.0, old_weight * 1.2)
                    updated = {"from": edge["from"], "to": edge["to"], "new_weight": edge["weight"]}
                    break
            if not updated and req.node_id:
                for edge in edges:
                    if edge.get("from") == req.node_id or edge.get("to") == req.node_id:
                        old_weight = edge.get("weight", 0.5)
                        edge["weight"] = min(1.0, old_weight * 1.2)
                        updated = {"from": edge["from"], "to": edge["to"], "new_weight": edge["weight"]}
                        break

        elif req.feedback_type == "incorrect_relation":
            # 关系错误 → weight *= 0.5
            for edge in edges:
                if (req.relation_from and req.relation_to
                        and edge.get("from") == req.relation_from
                        and edge.get("to") == req.relation_to):
                    old_weight = edge.get("weight", 0.5)
                    edge["weight"] = old_weight * 0.5
                    updated = {"from": edge["from"], "to": edge["to"], "new_weight": edge["weight"]}
                    break
            if not updated and req.node_id:
                for edge in edges:
                    if edge.get("from") == req.node_id or edge.get("to") == req.node_id:
                        old_weight = edge.get("weight", 0.5)
                        edge["weight"] = old_weight * 0.5
                        updated = {"from": edge["from"], "to": edge["to"], "new_weight": edge["weight"]}
                        break

        elif req.feedback_type == "update_node":
            # 更新节点 description
            for node in nodes:
                if node.get("id") == req.node_id:
                    if req.content:
                        node["description"] = req.content
                    updated = {"id": node["id"], "description": node["description"]}
                    break
            if not updated and req.content:
                # best-effort: 尝试匹配 label
                for node in nodes:
                    if req.content and node.get("label") == req.content:
                        updated = {"id": node["id"], "description": node["description"]}
                        break

        elif req.feedback_type == "new_relation":
            # 添加新关系
            new_edge = {
                "from": req.relation_from or req.node_id or "",
                "to": req.relation_to or "",
                "relation_type": "associate",
                "weight": 0.5,
            }
            edges.append(new_edge)
            updated = {"from": new_edge["from"], "to": new_edge["to"], "relation_type": "associate"}

        else:
            raise HTTPException(status_code=400, detail=f"未知反馈类型: {req.feedback_type}")

        # 写回
        store_knowledge_graph({"nodes": nodes, "edges": edges})

        return {"success": True, "message": "反馈已处理", "updated": updated}

    except HTTPException:
        raise
    except Exception as e:
        log.error("feedback_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"反馈处理失败: {str(e)}")
