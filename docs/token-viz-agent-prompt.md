# Token 可视化 Agent 任务提示词

## 任务目标

在"学科知识整合智能体"的 **QA 界面** 和 **对话界面** 添加 **Token 消耗统计**（每轮问答显示消耗的 token 数量）。

## 技术背景

- 后端 API（`POST /api/query` 和 `POST /api/chat`）返回时已在 response 中包含 token 统计
- 前端已有 `src/views/qa/QA.vue` 和 `src/views/chat/Chat.vue`
- 需要在前端展示这些统计数据

## 交付物

1. 修改 `src/views/qa/QA.vue` — 添加 token 统计展示
2. 修改 `src/views/chat/Chat.vue` — 添加 token 统计展示

## API 响应格式（参考）

后端应返回类似格式（如果还没加，让后端 Agent 补）：

```json
{
  "answer": "...",
  "sources": [...],
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 567,
    "total_tokens": 1801
  }
}
```

### 如果后端还没返回 usage

先在 QA 和 Chat 界面用 hardcoded 显示（等后端补）：
```js
const mockUsage = { prompt_tokens: 1200, completion_tokens: 300, total_tokens: 1500 }
```

后端 BE-5/BE-6 已完成，应该已经有 usage 字段。

## UI 设计

在回答内容下方加一行小字：

```
💬 消耗 Token: prompt=1,234 | completion=567 | 总计=1,801
```

样式：灰色小字，右对齐，不抢注意力。

## 验收标准

1. 每次提问/回答后，显示该轮的 token 消耗
2. 多轮对话时，每轮都显示各自的 token 消耗
3. 如果后端没返回 usage，前端显示 `---` 而不是报错

## 禁止事项

- ❌ 不改 API 契约
- ❌ 不做 token 统计的持久化（只显示当前轮）
- ❌ 不引入额外的图表库

## 开始

修改 `src/views/qa/QA.vue` 和 `src/views/chat/Chat.vue`。在 task-board.md 更新 FE-5 和 FE-6 状态。