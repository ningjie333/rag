# Few-Shot 示例 Agent 任务提示词

## 任务目标

在 `kg_extractor.py` 的知识点提取提示词中增加 **few-shot 示例**，提升 LLM 提取质量。

## 技术背景

- 文件：`backend/vector_store/kg_extractor.py`
- 当前提示词：`KG_EXTRACT_SYSTEM`（系统提示）和 `KG_EXTRACT_USER_TPL`（用户提示）
- 当前是 zero-shot（直接提取，无示例）

## 什么是 few-shot

在 prompt 中加入 1-3 个「输入→输出」示例，让 LLM 明白你期望的格式和质量：

```
示例输入：
"心肌炎是心肌的炎症性疾病，表现为心电图异常和肌钙蛋白升高。"

示例输出：
{
  "concepts": [
    {
      "term": "心肌炎",
      "description": "心肌的炎症性疾病",
      "aliases": ["心脏炎症"],
      "relatedTerms": ["心包炎", "心内膜炎"],
      "potentialPrerequisites": ["心脏解剖", "炎症反应"],
      "confidence": 0.95
    }
  ]
}
```

## 交付物

修改 `backend/vector_store/kg_extractor.py` 的 `KG_EXTRACT_SYSTEM` 字符串，在末尾添加：

```python
KG_EXTRACT_SYSTEM = """你是一个专业的知识分析专家。从教材文本中提取核心概念及其关系。
...（现有内容）...

## 输出示例

### 示例 1
输入文本：「心肌炎是心肌的炎症性疾病，表现为心电图 ST 段抬高和肌钙蛋白升高。」
输出：
{
  "concepts": [
    {
      "term": "心肌炎",
      "description": "心肌的炎症性疾病，表现为心电图异常和心肌损伤标志物升高",
      "aliases": ["心脏炎症"],
      "relatedTerms": ["心包积液", "心力衰竭"],
      "potentialPrerequisites": ["心脏解剖结构", "炎症反应机制"],
      "confidence": 0.95
    }
  ]
}

### 示例 2
输入文本：「炎症反应是机体对损伤因素的防御反应，包括红、肿、热、痛、功能障碍五大特征。」
输出：
{
  "concepts": [
    {
      "term": "炎症反应",
      "description": "机体对损伤的防御反应，表现为红肿热痛和功能障碍",
      "aliases": ["炎症", "发炎"],
      "relatedTerms": ["感染", "免疫反应", "组织损伤"],
      "potentialPrerequisites": ["组织学基础"],
      "confidence": 0.92
    }
  ]
}
```

## 验收标准

1. `kg_extractor.py` 中 `KG_EXTRACT_SYSTEM` 包含 `## 输出示例` 段落
2. 示例数量 ≥ 2 个
3. 示例格式与当前 schema 完全一致（aliases/relatedTerms/potentialPrerequisites/confidence）
4. 提示词末尾有"只输出 JSON，不要其他文字"

## 禁止事项

- ❌ 不改 schema 字段
- ❌ 不改 `extract_knowledge_graph()` 函数逻辑
- ❌ 不写测试

## 开始

修改 `backend/vector_store/kg_extractor.py`，在 `KG_EXTRACT_SYSTEM` 末尾加 2 个医学教材 few-shot 示例。