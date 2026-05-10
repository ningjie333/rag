"""向量检索引擎 v2 — Hybrid Search + GraphRAG

升级：BM25 文本检索 + RRF 合并 + GraphRAG 子图注入
"""
import structlog
from typing import Any

from config import settings
from .chroma_client import get_or_create_collection
from models.schemas import Citation

log = structlog.get_logger()


# ============ BM25 文本检索（轻量实现） ============

def _tokenize(text: str) -> list[str]:
    """简单分词：中文按单字，英文按空格"""
    import re
    tokens = re.findall(r"[一-鿿]+|[a-zA-Z0-9]+", text)
    words = []
    for t in tokens:
        if re.match(r"^[一-鿿]$", t):
            words.extend(list(t))
        elif len(t) > 1:
            words.append(t.lower())
    return words


def _bm25_score(query: str, doc_text: str, avgdl: float, k1: float = 1.5, b: float = 0.75) -> float:
    """简化的 BM25 评分"""
    query_words = _tokenize(query)
    doc_words = _tokenize(doc_text)
    doc_len = len(doc_words)
    word_freq = {}
    for w in doc_words:
        word_freq[w] = word_freq.get(w, 0) + 1

    score = 0.0
    for qw in query_words:
        if qw in word_freq:
            tf = word_freq[qw]
            idf = 1.0
            tf_norm = tf / (tf + k1 * (1 - b + b * doc_len / (avgdl + 1e-6)))
            score += idf * tf_norm
    return score


def _bm25_search(all_chunks: list[dict], query: str, top_k: int) -> list[tuple[str, float]]:
    """对所有 chunk 做 BM25 检索，返回 (chunk_id, score) 列表"""
    texts = [c["text"] for c in all_chunks]
    avgdl = sum(len(_tokenize(t)) for t in texts) / max(len(texts), 1)

    scored = []
    for c in all_chunks:
        score = _bm25_score(query, c["text"], avgdl)
        if score > 0:
            scored.append((c["chunk_id"], score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# ============ RRF 合并 ============

def rrf_fusion(
    vector_results: list[tuple[str, float]],
    bm25_results: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Reciprocal Rank Fusion：合并两个排序列表。
    score(doc_id) = Σ 1/(k + rank_in_list)
    """
    scores: dict[str, float] = {}
    for rank, (cid, _) in enumerate(vector_results):
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
    for rank, (cid, _) in enumerate(bm25_results):
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ============ GraphRAG：子图上下文注入 ============

def _load_merged_graph() -> dict | None:
    """从 ChromaDB KG collection 加载合并后的图谱"""
    try:
        collection = get_or_create_collection(settings.COLLECTION_KG)
        items = collection.get(
            where={"type": "node"},
            include=["documents", "metadatas"],
        )
        if not items.get("documents"):
            return None

        by_name: dict[str, list[str]] = {}
        by_id: dict[str, dict] = {}
        for doc, meta in zip(items["documents"], items["metadatas"]):
            import json
            node = json.loads(doc)
            by_id[node["id"]] = node
            name = node.get("label", node.get("name", ""))
            if name:
                by_name.setdefault(name, []).append(node["id"])

        edges = collection.get(
            where={"type": "edge"},
            include=["documents"],
        )
        edge_list = []
        if edges.get("documents"):
            for doc in edges["documents"]:
                edge_list.append(json.loads(doc))

        return {"nodes": list(by_id.values()), "edges": edge_list, "by_name": by_name, "by_id": by_id}
    except Exception as ex:
        log.warning("load_merged_graph failed: %s", ex)
        return None


def _match_entities(text: str, by_name: dict[str, list[str]], cap: int = 10) -> list[str]:
    """从文本中找 KG 节点名（最长匹配优先，避免子串冲突）"""
    hits: list[str] = []
    for name in sorted(by_name.keys(), key=len, reverse=True):
        if len(name) < 2:
            continue
        if name in text:
            for nid in by_name[name]:
                if nid not in hits:
                    hits.append(nid)
                    if len(hits) >= cap:
                        return hits
    return hits


def _format_graph_paths(merged: dict, entity_ids: list[str]) -> list[str]:
    """把 entity 及其 1-hop 邻域格式化为三元组字符串"""
    seen: set[tuple] = set()
    paths: list[str] = []
    eid_set = set(entity_ids)
    by_id = merged.get("by_id", {})

    for e in merged.get("edges", []):
        src, tgt = e.get("from", ""), e.get("to", "")
        if src not in eid_set and tgt not in eid_set:
            continue
        s_name = by_id.get(src, {}).get("label", src)
        t_name = by_id.get(tgt, {}).get("label", tgt)
        rt = e.get("relation_type", "associate")
        key = (s_name, rt, t_name)
        if key in seen:
            continue
        seen.add(key)
        paths.append(f"{s_name} -[{rt}]-> {t_name}")
        if len(paths) >= 30:
            break
    return paths


def get_graph_context(question: str, chunks: list[dict]) -> tuple[list[str], list[str]]:
    """
    GraphRAG：返回 (knowledge_paths, matched_entities)
    从 question 和 chunks 的文本中匹配 KG 节点，取 1-hop 邻域三元组。
    """
    merged = _load_merged_graph()
    if not merged:
        return [], []

    by_name = merged.get("by_name", {})
    by_id = merged.get("by_id", {})

    # 从 question 和 chunks 里匹配节点
    ent_ids: list[str] = []
    ent_ids.extend(_match_entities(question, by_name, cap=6))
    for c in chunks:
        for nid in _match_entities(c.get("text", ""), by_name, cap=4):
            if nid not in ent_ids:
                ent_ids.append(nid)
            if len(ent_ids) >= 16:
                break

    matched_names = [by_id[i].get("label", "") for i in ent_ids if i in by_id]
    paths = _format_graph_paths(merged, ent_ids)
    return paths, matched_names


# ============ 混合检索主函数 ============

def search_chunks(
    query: str,
    top_k: int = None,
    book_title: str = None,
    use_hybrid: bool = True,
) -> list[Citation]:
    """
    混合检索：向量检索 + BM25 + RRF 合并。

    Args:
        query: 查询文本
        top_k: 返回数量
        book_title: 过滤书籍
        use_hybrid: True=混合检索，False=纯向量检索
    """
    if top_k is None:
        top_k = settings.TOP_K

    collection = get_or_create_collection(settings.COLLECTION_CHUNKS)

    where_filter = {}
    if book_title:
        where_filter["book_title"] = book_title

    # 1. 向量检索（chromadb）
    n_results = top_k * 3 if use_hybrid else top_k
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter if where_filter else None,
        include=["documents", "metadatas", "distances"],
    )

    if not results or not results.get("ids"):
        return []

    vector_cids = results["ids"][0]
    vector_docs = results["documents"][0]
    vector_metas = results["metadatas"][0]
    vector_dists = results["distances"][0]

    if not use_hybrid:
        citations = []
        for cid, doc, meta, dist in zip(vector_cids, vector_docs, vector_metas, vector_dists):
            citations.append(Citation(
                chunk_id=cid,
                text=doc[:300] + "..." if len(doc) > 300 else doc,
                source=meta.get("source", ""),
                page=meta.get("page", 0),
                score=float(dist),
            ))
        return citations[:top_k]

    # 2. BM25 检索
    all_chunks_raw = collection.get(
        where=where_filter if where_filter else None,
        include=["documents", "metadatas", "ids"],
    )
    if all_chunks_raw.get("ids"):
        all_chunks_data = [
            {"chunk_id": cid, "text": doc}
            for cid, doc in zip(
                all_chunks_raw.get("ids", []),
                all_chunks_raw.get("documents", []),
            )
        ]
        bm25_results = _bm25_search(all_chunks_data, query, top_k * 3)
        bm25_cid_to_score = {cid: s for cid, s in bm25_results}
        bm25_ranked = [(cid, bm25_cid_to_score.get(cid, 0)) for cid, _ in bm25_results]
    else:
        bm25_ranked = []

    # 3. 向量结果按距离转 rank 分
    vec_cid_to_dist = {cid: d for cid, d in zip(vector_cids, vector_dists)}
    vector_ranked = [(cid, 1.0 / (d + 0.01)) for cid, d in zip(vector_cids, vector_dists)]

    # 4. RRF 合并
    fused = rrf_fusion(vector_ranked, bm25_ranked, k=60)
    fused_cids = [cid for cid, _ in fused[:top_k]]

    # 5. 构建结果（保留融合排序）
    cid_to_doc = {cid: doc for cid, doc in zip(vector_cids, vector_docs)}
    cid_to_meta = {cid: meta for cid, meta in zip(vector_cids, vector_metas)}

    all_cid_to_doc = dict(cid_to_doc)
    all_cid_to_meta = dict(cid_to_meta)
    if all_chunks_raw.get("ids"):
        for cid, doc, meta in zip(
            all_chunks_raw.get("ids", []),
            all_chunks_raw.get("documents", []),
            all_chunks_raw.get("metadatas", []),
        ):
            if cid not in all_cid_to_doc:
                all_cid_to_doc[cid] = doc
                all_cid_to_meta[cid] = meta

    citations = []
    for cid in fused_cids:
        doc = all_cid_to_doc.get(cid, "")
        meta = all_cid_to_meta.get(cid, {})
        citations.append(Citation(
            chunk_id=cid,
            text=doc[:300] + "..." if len(doc) > 300 else doc,
            source=meta.get("source", ""),
            page=meta.get("page", 0),
            score=0.5,
        ))

    return citations


def get_collection_stats() -> dict[str, int]:
    """获取各 collection 的记录数"""
    stats = {}
    for col_name in [settings.COLLECTION_CHUNKS, settings.COLLECTION_KG]:
        try:
            col = get_or_create_collection(col_name)
            stats[col_name] = col.count()
        except Exception:
            stats[col_name] = 0
    return stats