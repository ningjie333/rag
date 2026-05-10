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

### 改进方向（P1/P2/P3）

**P1 必做（2小时）：接入 bge-small-zh-v1.5 中文 embedding**
- 原因：当前 RAG 无 embedding 模型，只能用 ChromaDB 默认英文模型，中文教材检索质量严重不足
- 方式：`from sentence_transformers import SentenceTransformer; model = SentenceTransformer('BAAI/bge-small-zh-v1.5')`

**P2 时间允许（4小时）：异步图谱构建 + 进度查询**
- 原因：当前 /api/graph/build 是同步阻塞，大型教材（1000+ 页）会导致请求超时
- 方式：Celery + Redis 队列，前端轮询 /api/graph/status

**P3 远期：混合检索 + Rerank**
- 原因：BM25+RRF 已设计但 embedding 缺失导致效果打折，等 P1 稳定后再叠加

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

## 七、Prompt 设计

### RAG 问答 Prompt（query.py）

**System Prompt：**
```
你是一个专业的学科助教。基于检索到的教材内容和知识图谱上下文，准确回答学生问题。

要求：
1. 只基于提供的引用内容回答，不要编造
2. 如果引用内容不足以回答，明确说明
3. 回答要清晰、有条理，适当引用原文（用"【来源：页码】"标注）
4. 优先使用知识图谱中的关系路径来构建更完整的答案

回答格式：
[回答内容]
【来源：页码】
```

**User Prompt 模板：**
```
问题：{question}

参考内容：
{context}

{graph_section}
请基于以上内容回答问题。
```

其中 `graph_section` 注入格式：
```
知识图谱关系：
心肌炎 -[prerequisite]-> 心脏解剖结构
心肌炎 -[contains]-> 心电图 ST 段抬高

匹配的概念节点：心肌炎, 心脏解剖结构
```

### Few-Shot 示例（kg_extractor.py）

**输入：**
「心肌炎是心肌的炎症性疾病，表现为心电图 ST 段抬高和肌钙蛋白升高。」

**输出：**
```json
{
  "concepts": [{
    "term": "心肌炎",
    "description": "心肌的炎症性疾病，表现为心电图异常和心肌损伤标志物升高",
    "aliases": ["心脏炎症"],
    "relatedTerms": ["心包积液", "心力衰竭"],
    "potentialPrerequisites": ["心脏解剖结构", "炎症反应机制"],
    "confidence": 0.95
  }]
}
```

### 防幻觉策略

1. **temperature=0.1**：几乎确定性输出，减少随机编造
2. **强制引用编号**：每条回答必须标注【来源：页码】
3. **Few-Shot 示例**：通过示例约束输出格式和内容范围
4. **拒答机制**：引用不足时明确说明"资料不足以回答"

---

*文档版本：v1.0 | 更新：2026-05-10*