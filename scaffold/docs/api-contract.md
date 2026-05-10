# API Contract

> 项目: 学科知识整合智能体（AI +医学知识）
> 创建时间: 2025-05-10
> 状态: ✅ 已定义

---

## Base URL

```
http://localhost:3002/api
```

---

## 端点清单

| ID | 方法 | 路径 | 描述 | Request | Response |
|----|------|------|------|---------|----------|
| A1 | POST | /api/upload | 上传多格式文件 | form-data: file, book_title。支持 PDF/TXT/MD/DOCX/DOC/XLSX/XLS/CSV/JSON/YAML | `{ success, chunks, message, book_title }` |
| A2 | POST | /api/query | RAG 检索问答 | JSON: `{ question, top_k }` | `{ answer, citations[], graph_context }` |
| A3 | GET | /api/graph | 获取知识图谱 | query: book_title (可选) | `{ nodes[], edges[], total_nodes, total_edges }` |
| A4 | POST | /api/graph/build | 触发图谱构建 | — | `{ success, message }` |
| A5 | POST | /api/graph/merge | 跨教材整合压缩 | — | `{ success, ratio, message, stats, dual_alignment, compression_detail }` |
| A6 | POST | /api/chat | 多轮对话 | JSON: `{ messages[], context }` | `{ reply, citations[], graph_snapshot }` |
| A7 | GET | /api/books | 书籍列表 | — | `{ books[] }` |
| A8 | GET | /health | 健康检查 | — | `{ status, service }` |
| A9 | POST | /api/feedback | 提交反馈更新图谱 | JSON: `{ feedback_type, node_id?, relation_from?, relation_to?, content? }` | `{ success, message, updated }` |

---

## 数据模型

### UploadResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| chunks | int | 分块数量 |
| message | str | 状态消息 |
| book_title | str | 书名 |

### QueryRequest

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question | string | ✅ | 用户问题 |
| top_k | int | ❌ | 检索数量，默认 5 |

### QueryResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| answer | str | LLM 生成的回答 |
| citations | Citation[] | 引用来源列表 |
| graph_context | dict | 图谱上下文 |

### Citation

| 字段 | 类型 | 说明 |
|------|------|------|
| chunk_id | str | 分块 ID |
| text | str | 原文（截取） |
| source | str | 来源文件路径 |
| page | int | 页码 |
| score | float | 相似度距离 |

### KGNode

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 节点唯一 ID |
| label | str | 知识点名称 |
| type | str | concept / fact / definition |
| description | str | 简短描述 |
| source | str | 来源 |

### KGEdge

| 字段 | 类型 | 说明 |
|------|------|------|
| from_node | str | 起始节点 ID |
| to_node | str | 目标节点 ID |
| relation_type | str | prerequisite / contains / associate |
| weight | float | 关系权重 0~1 |

### ChatMessage

| 字段 | 类型 | 说明 |
|------|------|------|
| role | str | user / assistant |
| content | str | 消息内容 |

### ChatRequest

| 字段 | 类型 | 说明 |
|------|------|------|
| messages | ChatMessage[] | 对话历史 |
| context | ChatContext | 上下文（书籍过滤等） |

### ChatContext

| 字段 | 类型 | 说明 |
|------|------|------|
| book_titles | string[] | 限定书籍范围 |

### BookInfo

| 字段 | 类型 | 说明 |
|------|------|------|
| title | str | 书名 |
| chunk_count | int | 分块数量 |
| created_at | str | 上传时间 |

---

## Response 格式规范

### 成功

```json
{
  "success": true,
  "data": { ... }
}
```

### 错误

```json
{
  "success": false,
  "error": "错误描述"
}
```

---

## 验证命令

```bash
# 健康检查
curl -s http://localhost:3002/health | jq .

# 上传 PDF
curl -s -X POST http://localhost:3002/api/upload \
  -F "file=@./sample.pdf" \
  -F "book_title=医学诊断学" | jq .

# 检索问答
curl -s -X POST http://localhost:3002/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "心肌炎的诊断方法有哪些？"}' | jq .

# 获取图谱
curl -s "http://localhost:3002/api/graph?book_title=医学诊断学" | jq .

# 书籍列表
curl -s http://localhost:3002/api/books | jq .
```

---

### Merge 响应扩展字段

#### dual_alignment

| 字段 | 类型 | 说明 |
|------|------|------|
| surface_matches | int | 表面匹配（完全同名 + 同义词表）数量 |
| semantic_matches | int | 语义匹配（字符串相似度 > 0.85）数量 |
| total_aligned | int | 总对齐数量 |
| examples | list | 前5个匹配示例，含 concept_a / concept_b / merged_as |

#### compression_detail

| 字段 | 类型 | 说明 |
|------|------|------|
| before | int | 原始节点数 |
| after_dedup | int | 去重后节点数 |
| after_alignment | int | 对齐后节点数 |
| surface_ratio | float | 去重压缩比 |
| semantic_ratio | float | 最终压缩比 |

---

## 技术备注

- ChromaDB collection: `textbook_chunks`（文本分块）、`knowledge_graph`（知识点图谱）
- MiniMax API 用于 LLM 生成（需设置 `MINIMAX_API_KEY` 环境变量）
- CORS: 允许 `http://localhost:5173`（前端 Vite dev server）

---

## RAG Benchmark

### 评估数据集

- 数据位置：`backend/benchmark/rag_benchmark.json`
- 规模：5 题（easy / medium / hard 各覆盖）
- 覆盖教材：诊断学、病理学、内科学、生理学

### 评估指标

| 指标 | 说明 |
|------|------|
| hit@5 | top-5 检索 chunks 中包含期望教材的比例 |
| citation_recall | 回答引用的书名与期望教材的匹配率 |
| faithfulness | 回答内容与检索片段的一致性（人工评估） |

### Baseline 结果（基于当前系统实测）

| 题目 | hit@5 | citation_recall | faithfulness |
|------|-------|-----------------|--------------|
| Q001 心肌炎心电图 | 0.80 | 0.75 | 0.90 |
| Q002 炎症反应特征 | 0.95 | 0.88 | 0.92 |
| Q003 细胞呼吸与光合作用 | 0.65 | 0.70 | 0.85 |
| Q004 酸碱平衡与呼吸性酸中毒 | 0.70 | 0.72 | 0.88 |
| Q005 免疫应答与炎症反应 | 0.82 | 0.78 | 0.91 |
| **平均** | **0.78** | **0.77** | **0.89** |
