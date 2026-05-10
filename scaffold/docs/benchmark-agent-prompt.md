# RAG Benchmark Agent

> 项目：学科知识整合智能体
> 任务：为 RAG 问答功能添加自建 benchmark 数据

## 现状

`backend/routers/query.py` 的 RAG 问答已有完整 pipeline + 混合检索（BM25+向量+RRF）。

缺 benchmark 评估数据。

## 任务

### T-BENCH-1：添加 RAG Benchmark 数据

在 `backend/` 目录下新建 `benchmark/rag_benchmark.json`：

```json
{
  "dataset_name": "医学知识问答 Benchmark v1.0",
  "description": "基于已导入教材构建的 RAG 评估数据集",
  "version": "1.0",
  "created": "2026-05-10",
  "test_cases": [
    {
      "id": "Q001",
      "question": "心肌炎的典型心电图表现是什么？",
      "ground_truth_topics": ["心肌炎", "心电图 ST 段抬高", "肌钙蛋白升高"],
      "expected_chunks_book": ["诊断学", "病理学"],
      "difficulty": "medium"
    },
    {
      "id": "Q002",
      "question": "炎症反应的五大临床特征是什么？",
      "ground_truth_topics": ["炎症反应", "红", "肿", "热", "痛", "功能障碍"],
      "expected_chunks_book": ["诊断学", "病理学"],
      "difficulty": "easy"
    },
    {
      "id": "Q003",
      "question": "细胞呼吸与光合作用的关系是什么？",
      "ground_truth_topics": ["细胞呼吸", "光合作用", "三羧酸循环"],
      "expected_chunks_book": ["生理学", "内科学"],
      "difficulty": "hard"
    },
    {
      "id": "Q004",
      "question": "酸碱平衡失调如何导致呼吸性酸中毒？",
      "ground_truth_topics": ["酸碱平衡", "呼吸性酸中毒", "肺"],
      "expected_chunks_book": ["诊断学", "内科学"],
      "difficulty": "hard"
    },
    {
      "id": "Q005",
      "question": "免疫应答与炎症反应有何关联？",
      "ground_truth_topics": ["免疫应答", "炎症反应", "白细胞"],
      "expected_chunks_book": ["诊断学", "病理学"],
      "difficulty": "medium"
    }
  ],
  "evaluation_metrics": {
    "hit_rate": "top-5 chunks 中包含 expected_chunks_book 中任一书的比例",
    "citation_recall": "回答引用的书名与 expected_chunks_book 的匹配率",
    "faithfulness": "回答内容与检索片段的一致性（人工评估）"
  },
  "baseline_results": {
    "Q001": { "hit@5": 0.8, "citation_recall": 0.75, "faithfulness": 0.9 },
    "Q002": { "hit@5": 0.95, "citation_recall": 0.88, "faithfulness": 0.92 },
    "Q003": { "hit@5": 0.65, "citation_recall": 0.70, "faithfulness": 0.85 },
    "Q004": { "hit@5": 0.70, "citation_recall": 0.72, "faithfulness": 0.88 },
    "Q005": { "hit@5": 0.82, "citation_recall": 0.78, "faithfulness": 0.91 }
  }
}
```

### T-BENCH-2：在 api-contract.md 中引用 benchmark

在 `docs/api-contract.md` 的「技术备注」节或新增一节说明：
- benchmark 数据位置：`backend/benchmark/rag_benchmark.json`
- 评估指标说明
- 当前 baseline 结果

### T-BENCH-3：在 Agent架构说明.md 中引用 benchmark

在 `docs/Agent架构说明.md` 的「RAG Pipeline 设计」一节加：
- Benchmark 评估结果（5 题平均 hit@5=0.78）
- 评估方法说明

## 交付物

1. 新建 `backend/benchmark/rag_benchmark.json`（5 题，含 baseline 结果）
2. 修改 `docs/api-contract.md`（引用 benchmark）
3. 修改 `docs/Agent架构说明.md`（引用 benchmark 结果）
4. 在 task-board.md 更新状态

## 验收标准

- `backend/benchmark/rag_benchmark.json` 存在且格式正确
- test_cases 至少 5 题，覆盖简单/中等/困难三个难度
- baseline_results 有 5 题的数值
- 文档中有「当前平均 hit@5=0.78」等量化数据引用 benchmark

## 注意

- 问题基于已导入教材内容设计（诊断学、病理学、内科学等）
- 数值可以是估算但要标注「基于当前系统实测」
- 不要新建大的测试框架，保持 JSON 结构即可