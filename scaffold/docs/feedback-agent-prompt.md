# 反馈→图谱更新 Agent 任务提示词

## 任务目标

实现"多轮对话反馈修改知识图谱"功能：用户对回答的反馈能更新图谱节点/关系。

## 需求描述

用户对 AI 的回答进行反馈（如"这个关系不对"、"这个概念描述有误"），系统据此更新底层知识图谱。

## 技术方案

### API 扩展

新增接口 `POST /api/feedback`：

```python
@router.post("/feedback")
async def submit_feedback(
    feedback_type: str,   # "correct_relation" | "incorrect_relation" | "update_node" | "new_relation"
    node_id: str = None,
    relation_from: str = None,
    relation_to: str = None,
    content: str = None,  # 用户的纠正内容
):
```

### 反馈处理逻辑

1. **correct_relation / incorrect_relation** — 更新边的置信度
   - incorrect_relation → weight *= 0.5（降低）
   - correct_relation → weight = min(1.0, weight * 1.2)（提升）

2. **update_node** — 更新节点描述
   - 更新 ChromaDB KG collection 中该节点的 description

3. **new_relation** — 添加新关系
   - 在 KG collection 中新增一条边

### 存储更新

ChromaDB 的 KG collection 支持 `update` 操作，直接用 `upsert` 更新。

## 交付物

1. 修改 `routers/chat.py` 或新建 `routers/feedback.py`（推荐独立）
2. 添加反馈处理逻辑
3. 后端需要返回更新结果

### 扩展 QueryResponse / ChatResponse

在响应中可选择带上 `graph_snapshot`，供前端显示"图谱已更新"提示。

## 验收标准

1. `POST /api/feedback` 返回 200
2. 反馈后，`GET /api/graph` 能看到更新（如置信度变化）
3. 多轮反馈累积效果

## 禁止事项

- ❌ 不做 ACL/权限控制（单用户系统）
- ❌ 不做反馈持久化到独立表（直接更新 KG collection）
- ❌ 不写测试

## 开始

实现 `POST /api/feedback` 接口，处理 4 种反馈类型。更新 `docs/api-contract.md` 添加该接口。完成后在 task-board.md 记录。