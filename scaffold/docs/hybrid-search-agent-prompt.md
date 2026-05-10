# 混合检索 + Rerank Agent 任务提示词

## 任务目标

改进 `query_engine.py` 的 RAG 检索，实现**混合检索（Hybrid Search）+ Rerank**。

## 技术背景

- 文件：`backend/vector_store/query_engine.py`
- 当前：`search_chunks()` 只做简单向量相似度检索
- 问题：向量检索可能漏掉语义相近但 embedding 质量差的 chunk

## 混合检索原理

```
Query → 向量检索 (top_k*2) → 文本关键词检索 (top_k*2) → RRFL 合并 → Rerank → top_k
```

**两步合并：**
1. 向量检索（embedding similarity）
2. 关键词检索（BM25 / 词频）

**Rerank 原理：**
用更精确的模型（如 LLM）对比 top_k*2 的候选 chunk，重新排序输出 top_k。

## 交付物

修改 `backend/vector_store/query_engine.py`：

### 1. 新增 `bm25_search()` 函数

```python
def bm25_search(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """
    简单的 BM25 文本匹配。
    chunks: [{"text": "...", "chunk_id": "..."}, ...]
    返回 top_k 个最佳匹配的 chunk_id + score。
    """
    # 简单实现：用词频 TF 计算
    # 或用 rank_bm25 库（如果有）
```

### 2. 修改 `search_chunks()` 函数

```python
def search_chunks(question: str, top_k: int = 5, book_title: str = None) -> list[Citation]:
    # 1. 向量检索（chromadb similarity_search）
    vector_results = collection.query(query_texts=[question], n_results=top_k * 2, ...)

    # 2. 文本关键词检索
    bm25_results = bm25_search(question, all_chunks, top_k * 2)

    # 3. RRF 合并（Reciprocal Rank Fusion）
    # score = Σ 1/(k + rank)，k=60
    fused = rrf_fusion(vector_ranks, bm25_ranks, k=60)

    # 4. 取 top_k 个，用 LLM 做 Rerank（可选，有限速）
    # reranked = rerank_with_llm(question, fused[:top_k*2])[:top_k]

    # 5. 构建 Citation 返回
    return [Citation(...)]
```

### 3. 新增 RRF 合并函数

```python
def rrf_fusion(vector_results: list, bm25_results: list, k: int = 60) -> list:
    """
    Reciprocal Rank Fusion 合并两个排序列表。
    """
    scores = {}
    for rank, (chunk_id, score) in enumerate(vector_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
    for rank, (chunk_id, score) in enumerate(bm25_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

## 依赖

如需 BM25 库（可选，不强制）：
```bash
pip install rank-bm25
```
如果不用库，纯手写词频统计也可以工作。

## Rerank（可选，如果 miniMax API 限速可跳过）

```python
async def rerank_with_llm(question: str, candidates: list[dict]) -> list[dict]:
    """
    用 LLM 判断每个 chunk 对问题的相关度，返回排序后的列表。
    """
    # 构建 prompt：
    # "问题：{question}\n\n候选1：{chunk1_text}\n候选2：{chunk2_text}...\n
    #  请按与问题的相关度排序，返回 JSON: {ranking: [0, 2, 1, ...]}（数组为候选索引）"
    # 调用 MiniMax，解析返回的 ranking
```

## 验收标准

1. `POST /api/query` 返回的 citations 数量 ≥ top_k（即使合并后原始相关不足）
2. 向量检索和文本关键词检索同时生效
3. RRF 合并在两个结果之间产生差异化排序（不只是简单交集）

## 禁止事项

- ❌ 不改 API 接口格式（response 字段不变）
- ❌ 不引入大型 ML 库（仅 BM25 或纯词频）
- ❌ 不做 GPU 加速
- ❌ 不写测试

## 开始

修改 `backend/vector_store/query_engine.py`，先实现 BM25 搜索 + RRF 合并，再考虑 LLM Rerank。