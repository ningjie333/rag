"""LLM 知识点提取器 v2

升级：7类别枚举 + 强 prompt 约束 + few-shot 示例 + 低价值 chunk 过滤 + 多 agent 并行
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


# ============ 强约束 Prompt（7类别 + 4关系） ============

KG_EXTRACT_SYSTEM = """你是医学/学科知识图谱构建助手。从教材片段中提取知识点（节点）与知识点间关系（边）。

【硬约束】
1. category 必须从这7类中选一个：核心概念 / 现象 / 过程 / 结构 / 物质 / 疾病 / 方法
2. relation_type 必须是这4种之一：
   - prerequisite：A 是 B 的前置知识（理解 B 必须先理解 A）
   - parallel：同层级平行概念
   - contains： A 包含 B
   - applies_to：A 是 B 的应用场景
3. 只提取片段中明确出现的概念，不要发挥
4. definition 30~120字，必须基于原文
5. 单次输出 nodes ≤ 10 条，edges ≤ 12 条
6. **重要**：definition 和 description 的值中不要包含未转义的引号，不要在值末尾加冒号

【输出格式】严格 JSON（不要 markdown 包裹，不要有语法错误）：
{
  "nodes": [
    {"name": "动作电位", "definition": "细胞受刺激后膜电位的一次快速倒转", "category": "核心概念"}
  ],
  "edges": [
    {"source": "动作电位", "target": "静息电位", "relation_type": "prerequisite", "description": "理解动作电位需先掌握静息电位"}
  ]
}
{
  "nodes": [
    {"name": "动作电位", "definition": "细胞受刺激后膜电位的一次快速倒转", "category": "核心概念"}
  ],
  "edges": [
    {"source": "动作电位", "target": "静息电位", "relation_type": "prerequisite", "description": "理解动作电位需先掌握静息电位"}
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
    {"source": "心肌炎", "target": "心电图 ST 段抬高", "relation_type": "contains", "description": "心肌炎可导致 ST 段抬高"},
    {"source": "心肌炎", "target": "肌钙蛋白升高", "relation_type": "contains", "description": "心肌细胞损伤释放肌钙蛋白"},
    {"source": "心肌炎", "target": "心力衰竭", "relation_type": "applies_to", "description": "严重心肌炎可发展为心力衰竭"},
    {"source": "心电图 ST 段抬高", "target": "心肌炎", "relation_type": "prerequisite", "description": "识别心电图异常是诊断心肌炎的基础"}
  ]
}

输入：炎症反应是机体对损伤因子的防御反应，包括红、肿、热、痛、功能障碍五大特征。其本质是血管反应和白细胞渗出。
输出：
{
  "nodes": [
    {"name": "炎症反应", "definition": "机体对损伤因子的防御反应，表现为红肿热痛和功能障碍", "category": "过程"},
    {"name": "红", "definition": "炎症局部血管扩张充血，外观呈红色", "category": "现象"},
    {"name": "血管反应", "definition": "炎症时血管通透性增加和血流改变的统称", "category": "过程"}
  ],
  "edges": [
    {"source": "炎症反应", "target": "红", "relation_type": "contains", "description": "红是炎症的局部表现之一"},
    {"source": "炎症反应", "target": "血管反应", "relation_type": "contains", "description": "血管反应是炎症的本质过程"}
  ]
}

只输出 JSON，不要其他文字。"""

KG_EXTRACT_USER_TPL = """【教材】{source}
【正文】{chunk_text}

请输出符合格式的 JSON 对象。"""


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


async def _extract_single_chunk(chunk_data: dict, book_title: str) -> tuple[list, list]:
    """提取单个 chunk 的知识图谱（带并发控制）"""
    text = chunk_data["text"]
    source = chunk_data["metadata"].get("source", book_title)

    async with _get_llm_semaphore():
        kg_data = await extract_knowledge_graph(text, source=source)

    nodes = kg_data.get("nodes", [])
    edges = kg_data.get("edges", [])

    # 添加 source
    for node in nodes:
        node["source"] = book_title

    return nodes, edges


async def extract_knowledge_graph_batch(
    chunks: list[dict],
    book_title: str,
    max_concurrency: int = MAX_CONCURRENT_LLM,
) -> tuple[list, list]:
    """
    并行提取多个 chunk 的知识图谱。

    Args:
        chunks: [{"text": "...", "metadata": {...}}, ...]
        book_title: 教材标题
        max_concurrency: 最大并发数

    Returns:
        (all_nodes, all_edges)
    """
    total = len(chunks)
    log.info("batch_extract_start", total_chunks=total, max_concurrency=max_concurrency)

    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrency)

    async def extract_with_semaphore(chunk_data: dict, idx: int) -> tuple[list, list]:
        async with semaphore:
            nodes, edges = await _extract_single_chunk(chunk_data, book_title)
            if idx % 50 == 0:
                log.info("batch_progress", processed=idx + 1, total=total)
            return nodes, edges

    # 创建所有任务
    tasks = [
        extract_with_semaphore(chunk, i)
        for i, chunk in enumerate(chunks)
    ]

    # 并行执行
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

    log.info("batch_extract_done", total_nodes=len(all_nodes), total_edges=len(all_edges))
    return all_nodes, all_edges


def _fix_json_fixes(json_str: str) -> str:
    """修复 LLM 输出中常见的 JSON 语法错误"""
    # 1. 修复 "key":："value" -> "key": "value" (中文冒号 U+FF1A 在值前面)
    json_str = re.sub(r':：', ': "', json_str)
    # 2. 修复 "key": "value 而 value 中有未闭合的引号
    # 如果有 "text 后面没跟 " 且靠近行尾，补上 "
    json_str = re.sub(r'(":\s*")([^"]{3,60})([,\n}\]])', r'\1"\2"\3', json_str)
    # 3. 修复换行在字符串中间的情况
    json_str = re.sub(r'"([^"]*?)"\s*\n\s*"', lambda m: f'"{m.group(1)}"', json_str)
    return json_str


def _try_parse_json(raw: str) -> dict | None:
    """尝试解析 JSON，失败则尝试修复常见错误"""
    import json
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # 修复后重试
    fixed = _fix_json_fixes(raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # 二次修复：移除多余逗号
    fixed = fixed.replace(',}', '}').replace(',]', ']')
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


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


def _validate_node(n: dict, seen_names: set) -> dict | None:
    try:
        name = str(n["name"]).strip()
        definition = str(n.get("definition", name)).strip()[:200]
    except (KeyError, TypeError):
        return None
    if not name or len(name) > 40:
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
        raw_clean = _fix_json_fixes(raw_clean)
        data = _try_parse_json(raw_clean)
        if data is None:
            log.error("kg_extraction_parse_failed", raw=raw[:200] if raw else "")
            return {"nodes": [], "edges": []}
    except Exception as ex:
        log.error("kg_extraction_parse_failed", error=str(ex), raw=raw[:200] if raw else "")
        return {"nodes": [], "edges": []}

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