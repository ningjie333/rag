"""关系推理器

参考 Tutor-main/ConceptCorrelationService.cs 的多信号关联方法。

使用多信号关联发现概念之间的关系：
- 语义相似度（embedding 余弦相似度）
- LSH 近似匹配
- SimHash 词汇相似度
- 共现模式
- LLM 推理前置关系
"""
import json
import math
import re
import structlog
from difflib import SequenceMatcher
from typing import Optional

import httpx

from config import settings
from .chroma_client import get_or_create_collection

log = structlog.get_logger()

# 关系类型枚举（参考 Tutor 的 10 种关系类型，简化到 4 种）
RELATION_TYPES = {
    "prerequisite": "前置关系：A 是 B 的前置知识",
    "contains": "包含关系：A 包含 B",
    "associate": "关联关系：相关但不严格前置",
    "similarTo": "相似关系：相似易混淆",
}


async def call_llm(prompt: str, system: str = "") -> str:
    """通用 LLM 调用，支持 OpenAI / MiniMax"""
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return await call_openai(prompt, system)
    elif settings.MINIMAX_API_KEY and settings.MINIMAX_API_KEY not in ("your_api_key_here", "sk-...", ""):
        return await call_minimax(prompt, system)
    else:
        log.warning("No valid LLM API key configured")
        return '{"relationships": []}'


async def call_openai(prompt: str, system: str = "") -> str:
    """调用 OpenAI-compatible API"""
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": (
            [{"role": "system", "content": system}]
            if system
            else []
        ) + [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def call_minimax(prompt: str, system: str = "") -> str:
    """调用 MiniMax API"""
    if not settings.MINIMAX_API_KEY or settings.MINIMAX_API_KEY in ("your_api_key_here", "sk-...", ""):
        log.warning("MINIMAX_API_KEY not set or placeholder")
        return '{"relationships": []}'

    headers = {
        "Authorization": f"Bearer {settings.MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.MINIMAX_MODEL,
        "messages": (
            [{"role": "system", "content": system}]
            if system
            else []
        ) + [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.MINIMAX_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度"""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def hamming_distance(a: list[int], b: list[int]) -> int:
    """计算两个二值向量的汉明距离"""
    if len(a) != len(b):
        max_len = max(len(a), len(b))
        a = a + [0] * (max_len - len(a))
        b = b + [0] * (max_len - len(b))
    return sum(x != y for x, y in zip(a, b))


def simhash_signature(text: str, dim: int = 64) -> list[int]:
    """计算 SimHash 签名（简化版）"""
    # 实际应用中应使用更复杂的分词和哈希
    words = text.split()
    v = [0] * dim
    for word in words:
        h = hash(word) % (2**32)
        for i in range(dim):
            bit = (h >> i) & 1
            v[i] += 1 if bit else -1
    return [1 if vi > 0 else 0 for vi in v]


# LLM 关系推理提示词
RELATION_INFER_SYSTEM = """你是一个教育专家，分析概念之间的关系类型。

给定一对概念，分析它们的关系类型：
- prerequisite: A 是 B 的前置知识（要理解 B 必须先理解 A）
- contains: A 包含 B
- associate: 相关但不严格前置
- similarTo: 相似易混淆

返回 JSON：
{
  "relationships": [
    {
      "conceptA": "概念A名称",
      "conceptB": "概念B名称",
      "relationType": "prerequisite|contains|associate|similarTo",
      "direction": "AtoB|BtoA|bidirectional",
      "confidence": 0.85,
      "justification": "简要说明"
    }
  ]
}"""

RELATION_INFER_USER_TPL = """分析以下概念对之间的关系：

概念 A: {concept_a} - {desc_a}
概念 B: {concept_b} - {desc_b}

只返回 JSON，不要其他文字。"""


async def infer_relations_between_pair(
    concept_a: dict,
    concept_b: dict,
    semantic_sim: float = 0.0,
) -> Optional[dict]:
    """
    使用 LLM 推理两个概念之间的关系。

    Args:
        concept_a: 概念A {"term", "description", ...}
        concept_b: 概念B {"term", "description", ...}
        semantic_sim: 语义相似度（可选）

    Returns:
        关系 dict 或 None
    """
    prompt = RELATION_INFER_USER_TPL.format(
        concept_a=concept_a.get("term", ""),
        desc_a=concept_a.get("description", "")[:200],
        concept_b=concept_b.get("term", ""),
        desc_b=concept_b.get("description", "")[:200],
    )

    try:
        raw = await call_llm(prompt, RELATION_INFER_SYSTEM)
        raw_clean = re.sub(r"^```json\s*", "", raw.strip())
        raw_clean = re.sub(r"\s*```$", "", raw_clean.strip())
        data = json.loads(raw_clean)

        rels = data.get("relationships", [])
        if not rels:
            return None

        rel = rels[0]
        return {
            "from": concept_a.get("id", ""),
            "to": concept_b.get("id", ""),
            "relation_type": rel.get("relationType", "associate"),
            "direction": rel.get("direction", "AtoB"),
            "confidence": rel.get("confidence", 0.5),
            "justification": rel.get("justification", ""),
        }
    except Exception as e:
        log.error("relation_inference_failed", error=str(e))
        return None


SYNONYM_MAP = {
    "细胞呼吸": "呼吸作用",
    "呼吸作用": "细胞呼吸",
    "心肌炎症": "心肌炎",
    "心肌炎": "心肌炎症",
    "心音混浊": "心音异常",
    "心音异常": "心音混浊",
    "炎症反应": "炎性应答",
    "炎性应答": "炎症反应",
    "st段抬高": "st段上升",
    "st段上升": "st段抬高",
    "心电图异常": "ecg异常",
    "ecg异常": "心电图异常",
    "心衰": "心力衰竭",
    "心力衰竭": "心衰",
    "利尿": "利尿剂治疗",
    "利尿剂治疗": "利尿",
}


def dual_align_concepts(nodes: list[dict]) -> dict:
    surface_matches = []
    semantic_matches = []
    seen_pairs = set()

    node_names = [n.get("term", "") for n in nodes]

    for i in range(len(node_names)):
        for j in range(i + 1, len(node_names)):
            a = node_names[i].strip()
            b = node_names[j].strip()
            pair_key = tuple(sorted([a.lower(), b.lower()]))
            if pair_key in seen_pairs:
                continue

            if not a or not b:
                continue

            if a.lower() == b.lower():
                seen_pairs.add(pair_key)
                merged_as = a if len(a) >= len(b) else b
                surface_matches.append({
                    "concept_a": a,
                    "concept_b": b,
                    "merged_as": merged_as,
                })
                continue

            if a.lower() in SYNONYM_MAP and SYNONYM_MAP[a.lower()].lower() == b.lower():
                seen_pairs.add(pair_key)
                merged_as = a if len(a) >= len(b) else b
                surface_matches.append({
                    "concept_a": a,
                    "concept_b": b,
                    "merged_as": merged_as,
                })
                continue

            sim = SequenceMatcher(None, a.lower(), b.lower()).ratio()
            if sim > 0.85:
                seen_pairs.add(pair_key)
                merged_as = a if len(a) >= len(b) else b
                semantic_matches.append({
                    "concept_a": a,
                    "concept_b": b,
                    "merged_as": merged_as,
                    "similarity": round(sim, 2),
                })

    total_aligned = len(surface_matches) + len(semantic_matches)
    return {
        "surface_matches": surface_matches,
        "semantic_matches": semantic_matches,
        "total_aligned": total_aligned,
    }


async def infer_all_relations(concepts: list[dict]) -> list[dict]:
    """
    发现所有概念对之间的关系。

    使用多信号关联：
    1. 语义相似度（embedding）
    2. LSH 近似匹配
    3. SimHash 词汇相似度
    4. 共现模式
    5. LLM 推理

    Args:
        concepts: 概念列表

    Returns:
        关系列表
    """
    if len(concepts) < 2:
        return []

    # 计算所有概念对的分数
    pairs = []
    for i, a in enumerate(concepts):
        for j, b in enumerate(concepts):
            if i >= j:
                continue

            # 语义相似度（如果有 embedding）
            sem_sim = 0.0
            emb_a = a.get("embedding", [])
            emb_b = b.get("embedding", [])
            if emb_a and emb_b:
                sem_sim = cosine_similarity(emb_a, emb_b)

            # SimHash 词汇相似度
            sig_a = simhash_signature(f"{a.get('term', '')} {a.get('description', '')}")
            sig_b = simhash_signature(f"{b.get('term', '')} {b.get('description', '')}")
            simhash_sim = 1.0 - hamming_distance(sig_a, sig_b) / 64.0

            # 共现（shared aliases 或 relatedTerms）
            aliases_a = set(a.get("aliases", []))
            aliases_b = set(b.get("aliases", []))
            related_a = set(a.get("relatedTerms", []))
            related_b = set(b.get("relatedTerms", []))
            shared = len(aliases_a & aliases_b) + len(related_a & related_b)
            cooccur = min(shared / 3.0, 1.0)

            # 综合分数
            combined = sem_sim * 0.5 + simhash_sim * 0.3 + cooccur * 0.2

            pairs.append({
                "a": a,
                "b": b,
                "semantic_sim": sem_sim,
                "simhash_sim": simhash_sim,
                "cooccur": cooccur,
                "combined": combined,
            })

    # 按综合分数排序，取前 N 对用 LLM 推理
    pairs.sort(key=lambda x: x["combined"], reverse=True)
    top_pairs = pairs[: min(50, len(pairs))]  # 限制 LLM 调用次数

    relations = []
    for pair in top_pairs:
        rel = await infer_relations_between_pair(
            pair["a"], pair["b"], pair["semantic_sim"]
        )
        if rel:
            rel["weight"] = pair["combined"]
            relations.append(rel)

    return relations


def remove_cycles(relations: list[dict], concepts: list[dict]) -> list[dict]:
    """
    检测并移除图中的环。

    使用 DFS 检测环，移除造成环的边（优先移除低置信度边）。

    Args:
        relations: 关系列表
        concepts: 概念列表

    Returns:
        去环后的关系列表
    """
    # 构建邻接表
    adj = {}
    concept_ids = {c.get("id") for c in concepts}
    for rel in relations:
        if rel["from"] in concept_ids and rel["to"] in concept_ids:
            adj.setdefault(rel["from"], []).append(rel)

    # DFS 检测环
    def find_cycle():
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {cid: WHITE for cid in concept_ids}
        parent = {cid: None for cid in concept_ids}

        def dfs(node, path):
            color[node] = GRAY
            path.append(node)
            for rel in adj.get(node, []):
                neighbor = rel["to"]
                if color.get(neighbor) == GRAY:
                    # 找到环，返回环路径
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:]
                elif color.get(neighbor) == WHITE:
                    parent[neighbor] = node
                    cycle = dfs(neighbor, path[:])
                    if cycle:
                        return cycle
            color[node] = BLACK
            return None

        for cid in concept_ids:
            if color[cid] == WHITE:
                cycle = dfs(cid, [])
                if cycle:
                    return cycle
        return None

    # 迭代去环
    relations = relations[:]
    while True:
        cycle = find_cycle()
        if not cycle:
            break

        # 找环中最弱的边（最低置信度）
        weakest_idx = None
        weakest_conf = float("inf")
        for i in range(len(relations)):
            rel = relations[i]
            from_node = rel["from"]
            to_node = rel["to"]
            if from_node in cycle and to_node in cycle:
                idx_in_cycle = cycle.index(from_node)
                next_idx = (idx_in_cycle + 1) % len(cycle)
                if cycle[next_idx] == to_node:
                    conf = rel.get("confidence", 0.5)
                    if conf < weakest_conf:
                        weakest_conf = conf
                        weakest_idx = i

        if weakest_idx is not None:
            # 移除最弱边，或将其降级为 associate
            rel = relations[weakest_idx]
            rel["relation_type"] = "associate"
            rel["confidence"] = weakest_conf * 0.5
            log.info("cycle_removed", from_node=rel["from"], to_node=rel["to"])
        else:
            break

    return relations


def _is_similar(a: str, b: str, threshold: float = 0.7) -> bool:
    """编辑距离相似度判断"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


def _merge_two_concepts(existing: dict, concept: dict) -> dict:
    """合并两个概念，保留较长 description，合并列表字段"""
    # 保留较长 label/name
    name_a = existing.get("name", existing.get("term", ""))
    name_b = concept.get("name", concept.get("term", ""))
    if len(name_b) > len(name_a):
        if "name" in existing:
            existing["name"] = concept.get("name", name_b)
        if "term" in existing:
            existing["term"] = concept.get("term", name_b)

    # 合并 description：用逗号连接（去重）
    desc_a = existing.get("description", "")
    desc_b = concept.get("description", "")
    if desc_b and desc_b not in desc_a:
        existing["description"] = f"{desc_a}, {desc_b}" if desc_a else desc_b

    # 合并别名
    existing["aliases"] = list(set(existing.get("aliases", [])) | set(concept.get("aliases", [])))
    # 合并相关术语
    existing["relatedTerms"] = list(set(existing.get("relatedTerms", [])) | set(concept.get("relatedTerms", [])))
    # 合并前置知识
    existing["prerequisites"] = list(set(existing.get("prerequisites", [])) | set(concept.get("prerequisites", [])))
    # 使用较高 confidence
    existing["confidence"] = max(existing.get("confidence", 0), concept.get("confidence", 0))
    # 使用较长 description（长度优先策略）
    if len(concept.get("description", "")) > len(existing.get("description", "")):
        existing["description"] = concept["description"]
    # 合并来源
    sources = set(existing.get("sources", []))
    if concept.get("source"):
        sources.add(concept["source"])
    existing["sources"] = list(sources)
    return existing


def merge_duplicate_concepts(concepts: list[dict]) -> list[dict]:
    """
    合并重复概念。

    同名概念合并：aliases/relatedTerms/prerequisites 取并集，
    使用较高 confidence 和较长 description。

    语义对齐：label 编辑距离相似度 > 0.7 的概念也合并，
    保留较长 label，description 用逗号连接。

    Args:
        concepts: 概念列表

    Returns:
        去重后的概念列表
    """
    if not concepts:
        return []

    # 先标准化
    for c in concepts:
        c["aliases"] = c.get("aliases", [])
        c["relatedTerms"] = c.get("relatedTerms", [])
        c["prerequisites"] = c.get("prerequisites", [])
        c["sources"] = [c["source"]] if c.get("source") else []

    result = list(concepts)

    i = 0
    while i < len(result):
        j = i + 1
        while j < len(result):
            name_i = result[i].get("name", result[i].get("term", "")).strip()
            name_j = result[j].get("name", result[j].get("term", "")).strip()

            if not name_i or not name_j:
                j += 1
                continue

            # 精确匹配（不区分大小写）
            if name_i.lower() == name_j.lower():
                result[i] = _merge_two_concepts(result[i], result.pop(j))
                log.info("merge_exact", concept_a=name_i, concept_b=name_j)
                continue

            # 语义对齐：编辑距离相似度 > 0.7
            if _is_similar(name_i, name_j, threshold=0.7):
                # 保留较长 label
                if len(name_j) > len(name_i):
                    result[i], result[j] = result[j], result[i]
                result[i] = _merge_two_concepts(result[i], result.pop(j))
                log.info("merge_similar", concept_a=name_i, concept_b=name_j)
                continue

            j += 1
        i += 1

    return result
