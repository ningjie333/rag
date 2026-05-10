# Agent 架构说明

> 本文档描述学科知识整合智能体的多 Agent 架构设计。

## 一、架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Orchestrator (主协调)                      │
│  职责：任务拆解、派发、结果汇总、时间管控                          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │ Upload  │    │  Graph  │    │  Query  │
    │ Agent   │    │ Builder │    │ Agent   │
    │         │    │         │    │         │
    │ PDF解析  │    │ LLM提取  │    │ RAG检索  │
    │ 分块    │    │ 关系推理 │    │ 生成回答 │
    └─────────┘    └─────────┘    └─────────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
              ┌─────────▼─────────┐
              │    ChromaDB       │
              │  (向量+图谱存储)   │
              └───────────────────┘
```

## 二、各 Agent 职责

### 1. Upload Agent（上传解析）

**职责：**
- 接收 PDF/TXT/MD 文件
- 调用 PyMuPDF 解析 PDF
- 文本分块（chunk_size=500, overlap=50）
- 存入 ChromaDB textbook_chunks collection

**数据流：**
```
UploadFile → PDF解析 → 滑动窗口分块 → ChromaDB upsert
```

### 2. Graph Builder Agent（图谱构建）

**职责：**
- 从 ChromaDB 读取 chunks
- 调用 LLM 提取知识点（参考 Tutor ConceptExtractionService）
- 合并重复概念
- 推理概念间关系（参考 Tutor ConceptCorrelationService）
- 存储图谱到 KG collection

**核心模块：**
- `kg_extractor.py` — LLM 知识点提取
- `relation_inferrer.py` — 关系推理 + 去环 + 去重

### 3. Query Agent（检索问答）

**职责：**
- 接收用户问题
- 检索 ChromaDB 获取相关 chunks
- 调用 LLM 生成带引用回答
- 支持多轮对话上下文

**RAG Pipeline：**
```
问题 → 向量检索 → 获取 Top-K Chunks → 构建上下文 → LLM 生成 → 返回答案+引用
```

## 三、设计决策

### 决策 1：为何用 ChromaDB 而不是 FAISS？

**考量：**
- ChromaDB 支持元数据过滤（按 book_title 查询）
- Python 原生，部署简单
- 持久化存储，重启不丢失

**代价：**
- 性能略低于 FAISS（但够用）
- 占用更多内存

**结论：对黑客松场景，ChromaDB 更合适。**

### 决策 2：为何 LLM 提取代替正则？

**正则方案的问题（science-rag）：**
- 只识别 "Chapter X" 和公式
- 无法理解语义
- 图谱关系是假的（页码相邻=有关）

**LLM 方案的优势：**
- 理解文本语义
- 提取概念、定义、关系
- 自动发现前置知识

**代价：**
- 延迟增加（需调用 LLM）
- API 成本

**结论：对教育类文本，LLM 提取性价比高。**

### 决策 3：关系推理为何用多信号？

**单一信号的问题：**
- 语义相似度：对同义词敏感，可能漏掉相关概念
- 共现：不同章节共现的概念不一定相关

**多信号融合：**
| 信号 | 权重 | 说明 |
|------|------|------|
| 语义相似度 | 50% | embedding 余弦相似度 |
| SimHash | 30% | 词汇层面的相似度 |
| 共现 | 20% | 别名/相关术语重叠 |

**结论：多信号融合提高召回率。**

## 四、数据流链路

### 完整 Pipeline

```
1. 上传阶段
   PDF → Upload Agent → chunks → ChromaDB (textbook_chunks)

2. 图谱构建阶段
   ChromaDB → Graph Builder Agent → concepts → relations → ChromaDB (knowledge_graph)

3. 问答阶段
   用户问题 → Query Agent → ChromaDB 检索 → LLM 生成 → 回答+引用

4. 整合阶段
   多本教材 → Graph Builder → merge → 去重 → 压缩到 30%
```

### 跨教材整合流

```
Book A 图谱 ──┐
              ├──► merge_graphs() ──► 去重 ──► 压缩 ──► 合并图谱
Book B 图谱 ──┘                            │
                                          ▼
                                    ChromaDB (_merged_)
```

## 五、方案取舍与局限

### 取舍

| 取舍 | 原因 |
|------|------|
| 单 Agent 架构 | 黑客松时间紧迫，多 Agent 协作复杂度高 |
| ChromaDB | 开发速度 > 性能，元数据过滤是刚需 |
| MiniMax LLM | 国内可用，成本低 |

### 局限

| 局限 | 影响 | 改进方向 |
|------|------|---------|
| 无 embedding 模型 | 图谱节点无向量，无法做语义检索 | 接入 BGE/sentence-transformers |
| 内存存储对话 | 重启丢失 | 换 Redis |
| 无异步队列 | 图谱构建阻塞 API | 加 Celery/RQ |

### 改进方向（P1/P2）

1. **本地 embedding**：接入 sentence-transformers 中文模型
2. **异步构建**：图谱构建后台运行，支持进度查询
3. **混合检索**：向量 + BM25 + Rerank
4. **多图谱视图**：每个教材独立图谱 + 合并图谱切换

## 六、Mermaid 架构图

```mermaid
flowchart TD
    subgraph Upload["Upload Agent"]
        A1[PDF 文件] --> A2[pymupdf 解析]
        A2 --> A3[滑动窗口分块]
        A3 --> A4[ChromaDB upsert]
    end

    subgraph GraphBuilder["Graph Builder Agent"]
        B1[读取 chunks] --> B2[LLM 提取概念]
        B2 --> B3[merge_duplicate_concepts]
        B3 --> B4[infer_all_relations]
        B4 --> B5[remove_cycles]
        B5 --> B6[存储图谱]
    end

    subgraph Query["Query Agent"]
        C1[用户问题] --> C2[向量检索]
        C2 --> C3[构建上下文]
        C3 --> C4[LLM 生成]
        C4 --> C5[返回回答]
    end

    subgraph Storage["ChromaDB"]
        D1[textbook_chunks]
        D2[knowledge_graph]
    end

    Upload --> D1
    D1 --> GraphBuilder
    GraphBuilder --> D2
    D1 --> Query
```

---

*文档版本：v1.0 | 更新：2026-05-10*