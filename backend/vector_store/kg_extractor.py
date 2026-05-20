"""LLM 知识点提取器 v3

升级：两阶段提取（节点提取 → 全局关系推理）+ 优化三隐藏关系发现
阶段1：每个chunk → LLM只提取节点（不提取关系），节省50%调用量
阶段2：所有chunk节点合并后 → LLM全局推理跨chunk/跨教材深层关系
"""
import asyncio
import hashlib
import json
import re
import structlog
from typing import Any

import httpx

from config import settings
from .chroma_client import get_or_create_collection

log = structlog.get_logger()

# 允许的类别和关系（7类 + 4关系）
ALLOWED_CATEGORIES = {"核心概念", "现象", "过程", "结构", "物质", "疾病", "方法"}
ALLOWED_RELATIONS = {"prerequisite", "parallel", "contains", "applies_to"}
DEFAULT_CATEGORY = "核心概念"


async def call_llm(prompt: str, system: str = "") -> str:
    """通用 LLM 调用，支持 OpenAI / MiniMax"""
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return await call_openai(prompt, system)
    elif settings.MINIMAX_API_KEY and settings.MINIMAX_API_KEY not in ("your_api_key_here", "sk-...", ""):
        return await call_minimax(prompt, system)
    else:
        log.warning("No valid LLM API key configured")
        return '{"nodes":[],"edges":[]}'


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
        return '{"nodes":[],"edges":[]}'


# ============ Prompt 库（两阶段分离） ============

# 阶段1：节点+边提取 prompt
KG_NODE_EXTRACT_SYSTEM = """你是医学/学科知识图谱构建助手。从教材片段中提取知识点（节点）和它们之间的关系（边）。

【硬约束】
1. category 必须从这7类中选一个：核心概念 / 现象 / 过程 / 结构 / 物质 / 疾病 / 方法
2. relation_type 必须从这4类中选一个：prerequisite / parallel / contains / applies_to
3. 只提取片段中明确出现的概念和关系，不要发挥
4. definition 30~120字，必须基于原文；description 30~60字，描述推理依据
5. 单次输出 nodes ≤ 10 条，edges ≤ 6 条
6. **重要**：definition 值中不要包含未转义的引号，不要在值末尾加冒号
7. edges 中出现的 source 和 target 必须是 nodes 中已定义的节点名称

【输出格式】严格 JSON（不要 markdown 包裹，不要有语法错误）：
{
  "nodes": [
    {"name": "动作电位", "definition": "细胞受刺激后膜电位的一次快速倒转", "category": "核心概念"}
  ],
  "edges": [
    {"source": "心肌炎", "target": "心力衰竭", "relation_type": "applies_to", "description": "严重心肌炎可发展为心力衰竭", "weight": 0.8}
  ]
}

【Few-shot 示例】
输入：心肌炎是心肌的炎症性疾病，表现为心电图 ST 段抬高和肌钙蛋白升高。严重时可发展为心力衰竭。
输出：
{
  "nodes": [
    {"name": "心肌炎", "definition": "心肌的炎症性疾病，可由感染或自身免疫引起", "category": "疾病"},
    {"name": "心电图 ST 段抬高", "definition": "心电图上 ST 段相对于基线向上偏移，是心肌损伤的表现", "category": "现象"},
    {"name": "肌钙蛋白升高", "definition": "心肌损伤时肌钙蛋白释放入血，是诊断心肌炎的重要指标", "category": "现象"},
    {"name": "心力衰竭", "definition": "心脏泵血功能下降，无法满足机体需求", "category": "疾病"}
  ],
  "edges": [
    {"source": "心肌炎", "target": "心力衰竭", "relation_type": "applies_to", "description": "严重心肌炎可发展为心力衰竭", "weight": 0.8},
    {"source": "心肌炎", "target": "心电图 ST 段抬高", "relation_type": "applies_to", "description": "心肌炎常伴心电图 ST 段改变", "weight": 0.8}
  ]
}

输入：炎症反应是机体对损伤因子的防御反应，包括红、肿、热、痛、功能障碍五大特征。其本质是血管反应和白细胞渗出。
输出：
{
  "nodes": [
    {"name": "炎症反应", "definition": "机体对损伤因子的防御反应，表现为红肿热痛和功能障碍", "category": "过程"},
    {"name": "红", "definition": "炎症局部血管扩张充血，外观呈红色", "category": "现象"},
    {"name": "血管反应", "definition": "炎症时血管通透性增加和血流改变的统称", "category": "过程"},
    {"name": "白细胞渗出", "definition": "炎症时白细胞穿过血管壁到达炎症部位的过程", "category": "过程"}
  ],
  "edges": [
    {"source": "血管反应", "target": "炎症反应", "relation_type": "contains", "description": "血管反应是炎症反应的核心组成部分", "weight": 0.8},
    {"source": "白细胞渗出", "target": "炎症反应", "relation_type": "contains", "description": "白细胞渗出是炎症反应的关键过程", "weight": 0.8}
  ]
}

只输出 JSON，不要其他文字。"""

KG_NODE_EXTRACT_USER_TPL = """【教材】{source}
【正文】{chunk_text}

请输出符合格式的 JSON 对象。"""

# 阶段2：全局关系推理 prompt（基于已合并的全局节点）
KG_RELATION_INFER_SYSTEM = """你是医学跨章节关系推理助手。基于已提取的知识节点，推理它们之间的深层语义关联。

【节点来源】
来自多本医学教材，已完成跨章节合并。每个节点可能来自不同的教材上下文。

【关系类型】（必须选其一）
- prerequisite：A 是 B 的前置知识（理解 B 必须先理解 A）
- parallel：同层级平行概念
- contains： A 包含 B
- applies_to：A 是 B 的应用场景

【硬约束】
1. 只推理跨越不同教材/章节的隐藏关联，不要推理同章节内显而易见的共现关系
2. description 50字以内，描述推理依据
3. 单次输出 edges ≤ 20 条
4. **重要**：description 值中不要包含未转义的引号，不要在值末尾加冒号

【输出格式】严格 JSON（不要 markdown 包裹，不要有语法错误）：
{
  "edges": [
    {"source": "神经管分化", "target": "先天性巨细胞病毒感染", "relation_type": "prerequisite", "description": "神经管分化受阻是先天性CMV感染导致神经系统发育异常的基础", "weight": 0.8},
    {"source": "ACE2受体", "target": "急性呼吸窘迫综合征", "relation_type": "applies_to", "description": "SARS-CoV-2刺突蛋白结合ACE2受体是ARDS的启动环节", "weight": 0.8}
  ]
}

【Few-shot 示例】
输入节点：心肌炎、心力衰竭、心电图 ST 段抬高、肌钙蛋白升高、炎症反应、血管反应
输入来源：
- 心肌炎：病理学
- 心力衰竭：病理生理学
- 心电图 ST 段抬高：诊断学
- 炎症反应：病理学
输出：
{
  "edges": [
    {"source": "心肌炎", "target": "心力衰竭", "relation_type": "applies_to", "description": "严重心肌炎可发展为心力衰竭，是心内科重要病理过程", "weight": 0.8},
    {"source": "炎症反应", "target": "心肌炎", "relation_type": "contains", "description": "心肌炎是炎症反应在心肌的具体表现", "weight": 0.8}
  ]
}

只输出 JSON，不要其他文字。"""

KG_RELATION_INFER_USER_TPL = """【教材】{book_title}
【已提取的全局节点】（{node_count} 个）：
{nodes_list}

请输出符合格式的 JSON 对象，推理跨章节/跨教材的深层关联。"""


def _node_id(book_title: str, name: str) -> str:
    h = hashlib.md5(f"{book_title}|{name}".encode("utf-8")).hexdigest()[:8]
    safe = book_title.replace(" ", "_").replace("/", "_")
    return f"{safe}::node_{h}"


# 并发控制：最大同时 LLM 调用数
MAX_CONCURRENT_LLM = 5
_llm_semaphore: asyncio.Semaphore | None = None

def _get_llm_semaphore() -> asyncio.Semaphore:
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM)
    return _llm_semaphore


async def _extract_nodes_and_edges(chunk_data: dict, book_title: str) -> tuple[list, list]:
    """阶段1：提取单个 chunk 的节点和边（per-chunk 关系提取）"""
    text = chunk_data["text"]
    source = chunk_data["metadata"].get("source", book_title)

    if _is_noise_chunk(text):
        return [], []

    title = source.split("/")[-1].replace(".pdf", "") if source else book_title

    # Mock extraction when no API key
    if (not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ("", "your_api_key_here")) and \
       (not settings.MINIMAX_API_KEY or settings.MINIMAX_API_KEY in ("your_api_key_here", "sk-...", "")):
        words = re.findall(r'[一-鿿]{3,8}', text[:500])
        seen = set()
        nodes = []
        for word in words:
            if word in seen or len(word) < 3:
                continue
            seen.add(word)
            node_id = f"mock_{hashlib.md5(word.encode()).hexdigest()[:8]}"
            nodes.append({"id": node_id, "name": word, "label": word, "type": "concept",
                          "description": f"概念: {word[:15]}", "source": book_title,
                          "category": "核心概念", "confidence": 0.5})
        edges = []
        for i in range(min(len(nodes), 5)):
            for j in range(i+1, min(len(nodes), 8)):
                if i != j:
                    edges.append({"from": nodes[i]["id"], "to": nodes[j]["id"], "source": nodes[i]["name"], "target": nodes[j]["name"], "relation_type": "associate", "description": "共现关系", "weight": 0.5})
        return nodes, edges

    prompt = KG_NODE_EXTRACT_USER_TPL.format(source=title, chunk_text=text.strip()[:3000])

    raw = None
    last_err = None
    for attempt in range(2):
        try:
            raw = await call_llm(prompt, KG_NODE_EXTRACT_SYSTEM)
            break
        except Exception as ex:
            last_err = ex
            log.warning("kg_node_retry", attempt=attempt + 1, error=str(ex))
            if attempt == 0:
                await asyncio.sleep(1)

    if raw is None:
        log.error("kg_node_api_failed", error=str(last_err))
        return [], []

    try:
        raw_clean = re.sub(r"^```json\s*", "", raw.strip())
        raw_clean = re.sub(r"\s*```$", "", raw_clean.strip())
        raw_clean = _fix_json_fixes(raw_clean)
        data = json.loads(raw_clean)
    except Exception:
        try:
            match = re.search(r'\{[\s\S]*"nodes"[\s\S]*\}', raw)
            data = json.loads(match.group()) if match else {"nodes": []}
        except Exception:
            data = {"nodes": []}

    raw_nodes = data.get("nodes", []) if isinstance(data, dict) else []
    raw_edges = data.get("edges", []) if isinstance(data, dict) else []
    nodes = []
    seen_ids = set()
    name_to_id = {}
    for n in raw_nodes:
        try:
            name = str(n["name"]).strip()
            definition = str(n.get("definition", name)).strip()[:200]
        except (KeyError, TypeError):
            continue
        if not name or len(name) > 40 or _is_noise_node(name):
            continue
        category = str(n.get("category", DEFAULT_CATEGORY)).strip()
        if category not in ALLOWED_CATEGORIES:
            category = DEFAULT_CATEGORY
        node_id = _node_id(book_title, name)
        if node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        name_to_id[name] = node_id
        nodes.append({
            "id": node_id,
            "name": name,
            "label": name,
            "type": category,
            "description": definition,
            "source": book_title,
            "category": category,
            "confidence": 0.9,
        })

    edges = []
    for e in raw_edges:
        try:
            source = str(e["source"]).strip()
            target = str(e["target"]).strip()
            rt = str(e.get("relation_type", "")).strip()
            if not source or not target or source == target:
                continue
            if source not in name_to_id or target not in name_to_id:
                continue
            if rt not in ALLOWED_RELATIONS:
                continue
            desc = str(e.get("description", "")).strip()[:60]
            weight = float(e.get("weight", 0.8))
            edges.append({
                "from": name_to_id[source],
                "to": name_to_id[target],
                "relation_type": rt,
                "description": desc,
                "weight": weight,
            })
        except (KeyError, TypeError):
            continue

    return nodes, edges


def _merge_nodes(all_nodes: list) -> tuple[list, dict]:
    """节点去重合并，返回 (merged_nodes, name_to_id)"""
    name_to_id = {}
    merged = []
    seen_ids = set()

    for n in all_nodes:
        nid = n.get("id", "")
        name = n.get("name", "")
        if not name or nid in seen_ids:
            continue
        seen_ids.add(nid)
        name_to_id[name] = nid
        merged.append(n)

    return merged, name_to_id


async def _infer_global_relations(merged_nodes: list, existing_edges: list, chunks: list, book_title: str) -> list:
    """阶段2：基于全局节点推理跨 chunk 深层关系（补充 per-chunk 边）

    Args:
        merged_nodes: 去重后的节点列表
        existing_edges: per-chunk 已提取的边列表（去重后）
        chunks: 原始 chunk 列表（用于获取来源信息）
        book_title: 教材标题
    """
    if len(merged_nodes) < 2:
        return []

    # 构建已有关系列（用于过滤重复）
    existing_rels = set()
    for e in existing_edges:
        from_id = e.get("from", "")
        to_id = e.get("to", "")
        rt = e.get("relation_type", "")
        if from_id and to_id:
            existing_rels.add((from_id, to_id, rt))

    nodes_list = "\n".join([f"- {n['name']}: {n.get('description', '')[:50]}" for n in merged_nodes[:50]])
    prompt = KG_RELATION_INFER_USER_TPL.format(
        book_title=book_title,
        node_count=len(merged_nodes),
        nodes_list=nodes_list
    )

    raw = None
    for attempt in range(2):
        try:
            raw = await call_llm(prompt, KG_RELATION_INFER_SYSTEM)
            break
        except Exception as ex:
            log.warning("kg_relation_infer_retry", attempt=attempt + 1, error=str(ex))
            if attempt == 0:
                await asyncio.sleep(1)

    if raw is None:
        return []

    try:
        raw_clean = re.sub(r"^```json\s*", "", raw.strip())
        raw_clean = re.sub(r"\s*```$", "", raw_clean.strip())
        raw_clean = _fix_json_fixes(raw_clean)
        data = json.loads(raw_clean)
    except Exception:
        try:
            match = re.search(r'\{[\s\S]*"edges"[\s\S]*\}', raw)
            data = json.loads(match.group()) if match else {"edges": []}
        except Exception:
            data = {"edges": []}

    raw_edges = data.get("edges", []) if isinstance(data, dict) else []
    name_to_id = {n["name"]: n["id"] for n in merged_nodes}
    edges = []

    for e in raw_edges:
        try:
            source = str(e["source"]).strip()
            target = str(e["target"]).strip()
            rt = str(e.get("relation_type", "")).strip()
            desc = str(e.get("description", "")).strip()[:60]
        except (KeyError, TypeError):
            continue
        if not source or not target or source == target:
            continue
        if source not in name_to_id or target not in name_to_id:
            continue
        if rt not in ALLOWED_RELATIONS:
            continue
        weight = float(e.get("weight", 0.8))
        edges.append({
            "from": name_to_id[source],
            "to": name_to_id[target],
            "relation_type": rt,
            "description": desc,
            "weight": weight,
        })

    return edges


async def extract_knowledge_graph_batch(
    chunks: list[dict],
    book_title: str,
    max_concurrency: int = MAX_CONCURRENT_LLM,
) -> tuple[list, list]:
    """
    两阶段提取知识图谱：
    阶段1：每个chunk → LLM只提取节点（不提取关系）
    阶段2：所有chunk节点合并后 → LLM全局推理跨chunk关系

    Args:
        chunks: [{"text": "...", "metadata": {...}}, ...]
        book_title: 教材标题
        max_concurrency: 最大并发数

    Returns:
        (all_nodes, all_edges)
    """
    total = len(chunks)
    log.info("batch_extract_start", total_chunks=total, max_concurrency=max_concurrency, stage="two_phase_v2")

    # ===== 阶段1：节点+边提取 =====
    semaphore = asyncio.Semaphore(max_concurrency)

    async def extract_chunk(chunk_data: dict, idx: int) -> tuple[list, list]:
        async with semaphore:
            nodes, edges = await _extract_nodes_and_edges(chunk_data, book_title)
            if idx % 100 == 0:
                log.info("batch_progress", stage="nodes", processed=idx + 1, total=total)
            return nodes, edges

    tasks = [extract_chunk(chunk, i) for i, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_nodes = []
    all_edges = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            log.warning("chunk_extract_failed", idx=i, error=str(result))
            continue
        nodes, edges = result
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    log.info("stage1_done", total_raw_nodes=len(all_nodes), total_raw_edges=len(all_edges))

    # 节点去重合并
    merged_nodes, name_to_id = _merge_nodes(all_nodes)
    log.info("nodes_merged", before=len(all_nodes), after=len(merged_nodes))

    # 边去重（基于 from+to+relation 唯一性）
    seen_edges = set()
    dedup_edges = []
    for e in all_edges:
        key = (e.get("from", ""), e.get("to", ""), e.get("relation_type", ""))
        if key not in seen_edges:
            seen_edges.add(key)
            dedup_edges.append(e)
    log.info("edges_dedup", before=len(all_edges), after=len(dedup_edges))

    # ===== 阶段2：全局关系推理（补充跨chunk深层关系） =====
    log.info("stage2_start", total_nodes=len(merged_nodes), total_edges=len(dedup_edges))
    global_edges = await _infer_global_relations(merged_nodes, dedup_edges, chunks, book_title)
    log.info("stage2_done", inferred_edges=len(global_edges))

    # 合并 per-chunk 边 + 全局推理边
    combined_edges = dedup_edges + global_edges
    # 再去重一次（防止全局推理的边和 per-chunk 边重复）
    final_edges = []
    seen_final = set()
    for e in combined_edges:
        key = (e.get("from", ""), e.get("to", ""), e.get("relation_type", ""))
        if key not in seen_final:
            seen_final.add(key)
            final_edges.append(e)

    log.info("batch_extract_done", total_nodes=len(merged_nodes), total_edges=len(final_edges))
    return merged_nodes, final_edges


def _fix_json_fixes(json_str: str) -> str:
    """修复 LLM 输出中常见的 JSON 语法错误"""
    # 1. 修复 "key":："value" -> "key": "value" (全角冒号 U+FF1A 紧跟 ASCII 冒号后)
    # 模式: "key":："value" = quote + fullwidth-colon + quote
    # 替换为: quote + ASCII-colon + quote
    json_str = json_str.replace('："', ':"')
    return json_str


def _is_noise_chunk(chunk_text: str) -> bool:
    """过滤目录/版权/前言等低价值 chunk"""
    if len(chunk_text.strip()) < 80:
        return True
    noise_keywords = (
        "修订说明", "前言", "编委", "目录", "版权", "出版", "致谢",
        "序言", "总序", "审稿", "主编", "副主编", "策划编辑",
    )
    for kw in noise_keywords:
        if kw in chunk_text[:60]:
            return True
    return False


def _is_noise_node(name: str) -> bool:
    """过滤主编/出版社等元数据词汇"""
    noise_terms = (
        "主编", "副主编", "编委", "作者", "出版", "出版社",
        "人民卫生", "编写", "修订", "审稿", "策划", "编辑",
        "第版", "第版", "版次", "字数", "印数", "定价",
        "卞修武", "李一雷", "王国平", "刘秀萍", "张红英", "陈国强",
        "钱睿哲", "姜志胜", "刘金保", "张敏",
    )
    for term in noise_terms:
        if term in name:
            return True
    return False


def _validate_node(n: dict, seen_names: set) -> dict | None:
    try:
        name = str(n["name"]).strip()
        definition = str(n.get("definition", name)).strip()[:200]
    except (KeyError, TypeError):
        return None
    if not name or len(name) > 40:
        return None
    if _is_noise_node(name):
        return None
    category = str(n.get("category", DEFAULT_CATEGORY)).strip()
    if category not in ALLOWED_CATEGORIES:
        category = DEFAULT_CATEGORY
    return {"name": name, "definition": definition, "category": category}


def _validate_edge(e: dict, name_to_id: dict) -> dict | None:
    try:
        source = str(e["source"]).strip()
        target = str(e["target"]).strip()
        rt = str(e.get("relation_type", "")).strip()
    except (KeyError, TypeError):
        return None
    if not source or not target or source == target:
        return None
    if source not in name_to_id or target not in name_to_id:
        return None
    if rt not in ALLOWED_RELATIONS:
        return None
    desc = str(e.get("description", "")).strip()[:60]
    return {
        "from": name_to_id[source],
        "to": name_to_id[target],
        "relation_type": rt,
        "description": desc,
        "weight": 0.8,
    }


async def extract_knowledge_graph(chunk_text: str, source: str = "") -> dict:
    """从文本块提取知识图谱节点和边（7类别 + 4关系）"""
    if _is_noise_chunk(chunk_text):
        return {"nodes": [], "edges": []}

    book_title = source.split("/")[-1].replace(".pdf", "") if source else "unknown"

    # Mock extraction when no API key
    if (not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ("", "your_api_key_here")) and \
       (not settings.MINIMAX_API_KEY or settings.MINIMAX_API_KEY in ("your_api_key_here", "sk-...", "")):
        log.warning("No valid LLM API key configured, using mock extraction")
        # 匹配连续的中文字符
        words = re.findall(r'[一-鿿]{3,8}', chunk_text[:500])
        # 去重并过滤太短的
        seen = set()
        nodes = []
        edges = []
        for word in words:
            if word in seen or len(word) < 3:
                continue
            seen.add(word)
            node_id = f"mock_{hashlib.md5(word.encode()).hexdigest()[:8]}"
            nodes.append({"id": node_id, "name": word, "label": word, "type": "concept", "description": f"概念: {word[:15]}", "source": book_title, "category": "核心概念", "confidence": 0.5})
        # 生成简单的共现边
        for i in range(min(len(nodes), 5)):
            for j in range(i+1, min(len(nodes), 8)):
                if i != j:
                    edges.append({"from": nodes[i]["id"], "to": nodes[j]["id"], "source": nodes[i]["name"], "target": nodes[j]["name"], "relation_type": "associate", "description": "共现关系", "weight": 0.5})
        return {"nodes": nodes, "edges": edges}

    prompt = KG_EXTRACT_USER_TPL.format(
        source=book_title,
        chunk_text=chunk_text.strip()[:3000],
    )

    raw = None
    last_err = None
    for attempt in range(2):
        try:
            raw = await call_llm(prompt, KG_EXTRACT_SYSTEM)
            break
        except Exception as ex:
            last_err = ex
            log.warning("kg_minimax_retry", attempt=attempt + 1, error=str(ex))
            if attempt == 0:
                import asyncio
                await asyncio.sleep(1)

    if raw is None:
        log.error("kg_extraction_api_failed", error=str(last_err))
        return {"nodes": [], "edges": []}

    try:
        raw_clean = re.sub(r"^```json\s*", "", raw.strip())
        raw_clean = re.sub(r"\s*```$", "", raw_clean.strip())
        # 修复 LLM 常见的 JSON 错误
        raw_clean = _fix_json_fixes(raw_clean)
        data = json.loads(raw_clean)
    except Exception as ex:
        # 如果还是失败，尝试用 regex 提取第一个完整的 JSON 对象
        try:
            match = re.search(r'\{[\s\S]*"nodes"[\s\S]*\}', raw)
            if match:
                data = json.loads(match.group())
            else:
                data = {"nodes": [], "edges": []}
        except Exception:
            data = {"nodes": [], "edges": []}

    raw_nodes = data.get("nodes", []) if isinstance(data, dict) else []
    raw_edges = data.get("edges", []) if isinstance(data, dict) else []

    nodes, name_to_id = [], {}
    seen_ids = set()
    for n in raw_nodes:
        v = _validate_node(n, seen_ids)
        if not v:
            continue
        node_id = _node_id(book_title, v["name"])
        if node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        name_to_id[v["name"]] = node_id
        nodes.append({
            "id": node_id,
            "name": v["name"],  # KGNode schema expects 'name' field
            "label": v["name"],
            "type": v["category"],
            "description": v["definition"],
            "source": book_title,
            "category": v["category"],
            "confidence": 0.9,
        })

    edges = []
    for e in raw_edges:
        v = _validate_edge(e, name_to_id)
        if v:
            edges.append(v)

    return {"nodes": nodes, "edges": edges}


def store_knowledge_graph(kg_data: dict, book_title: str = ""):
    """将提取的知识图谱存入 FAISS"""
    collection = get_or_create_collection(settings.COLLECTION_KG)
    nodes = kg_data.get("nodes", [])
    edges = kg_data.get("edges", [])

    # Use dummy vectors for KG storage (FAISS requires vectors)
    dim = 128
    dummy_vector = [0.0] * dim

    node_ids = [n["id"] for n in nodes]
    node_metas = [{"type": "node", "book_title": book_title, "label": n.get("label", n.get("name", "")), "data": json.dumps(n, ensure_ascii=False)} for n in nodes]
    node_docs = [n.get("label", n.get("name", "")) for n in nodes]

    edge_ids = [f"e_{i}" for i in range(len(edges))]
    edge_metas = [{"type": "edge", "book_title": book_title, "data": json.dumps(e, ensure_ascii=False)} for e in edges]
    edge_docs = [json.dumps(e, ensure_ascii=False) for e in edges]

    if node_ids:
        collection.upsert(ids=node_ids, vectors=[dummy_vector] * len(node_ids), metadatas=node_metas, documents=node_docs)
    if edge_ids:
        collection.upsert(ids=edge_ids, vectors=[dummy_vector] * len(edge_ids), metadatas=edge_metas, documents=edge_docs)

    log.info("kg_stored", node_count=len(nodes), edge_count=len(edges))


def get_full_graph(book_title: str = None) -> dict:
    """获取完整知识图谱"""
    collection = get_or_create_collection(settings.COLLECTION_KG)

    nodes, edges = [], []

    # 获取所有 nodes
    node_filter = {"type": "node"}
    if book_title:
        node_filter["book_title"] = book_title
    node_items = collection.get(where=node_filter)
    for meta in node_items.get("metadatas", []):
        data_str = meta.get("data", "{}")
        item = json.loads(data_str)
        nodes.append(item)

    # 获取所有 edges
    edge_filter = {"type": "edge"}
    if book_title:
        edge_filter["book_title"] = book_title
    edge_items = collection.get(where=edge_filter)
    for meta in edge_items.get("metadatas", []):
        data_str = meta.get("data", "{}")
        item = json.loads(data_str)
        edges.append(item)

    return {"nodes": nodes, "edges": edges}