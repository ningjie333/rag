# 前端 Agent 任务提示词

## 项目概况

**项目名称**：学科知识整合智能体
**技术栈**：Vue 3 + TypeScript + Vite 6 + AntV G6
**后端**：Python FastAPI (localhost:3002)
**前端**：Vue3 SPA (localhost:5173)

---

## 你的任务（FE-1 ~ FE-8）

### FE-1 【起步】Vue3 SPA 骨架 + 路由
- 已有 `src/` 目录结构和基础组件（Sidebar/TopBar/EmptyState/LoadingSpinner/StatCard/PageHeader）
- 已有 `src/router/index.ts` 路由配置
- 已有 `src/api/client.ts`（API 客户端，端口已改为 3002）
- **你的任务**：补充缺失的路由页面，创建 `src/views/` 下的视图组件

### FE-2 【教材上传组件】
- 创建 `src/views/upload/Upload.vue`
- 功能：拖拽上传 PDF/TXT，显示文件名 + 解析状态进度条
- 调用 `POST /api/upload`（form-data: file, book_title）
- 验收：`curl -X POST http://localhost:3002/api/upload` 能看到响应

### FE-3 【图谱可视化】
- 创建 `src/views/graph/Graph.vue`
- 使用 AntV G6 渲染知识图谱
- 功能：显示节点+边、缩放、拖拽、点击节点
- 调用 `GET /api/graph` 获取数据
- **mock 数据可用**：先用自己的 mock 数据渲染图谱，不等后端

### FE-4 【图谱交互】
- 基于 FE-3，添加交互功能
- 点击节点弹出详情（label/description/source）
- 节点大小/颜色映射知识点出现频次
- 不同教材节点分色标识

### FE-5 【RAG 问答界面】
- 创建 `src/views/qa/QA.vue`
- 输入框提问，显示 AI 回答 + 引用来源列表
- 调用 `POST /api/query`（`{ question, top_k }`）
- **mock 数据可用**：先用 hardcoded 回答测试 UI

### FE-6 【多轮对话界面】
- 创建 `src/views/chat/Chat.vue`
- 对话历史可见，能继续追问
- 调用 `POST /api/chat`（`{ messages[], context }`）
- **mock 数据可用**

### FE-7 【报告预览/下载】
- 创建 `src/views/report/Report.vue`
- 调用 `GET /api/report` 获取 Markdown 报告
- 预览 Markdown 格式，支持下载
- **mock 数据可用**

### FE-8 【SPA 布局整合】
- 修改 `src/App.vue` 实现三栏布局（1920×1080）
- 左侧：教材管理（上传列表）
- 中间：图谱可视化
- 右侧：Tab 面板（问答/对话/报告）

---

## API 契约（参考 docs/api-contract.md）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传 PDF/TXT，form-data |
| `/api/query` | POST | RAG 问答，body: `{ question, top_k }` |
| `/api/graph` | GET | 获取图谱 `{ nodes[], edges[] }` |
| `/api/chat` | POST | 多轮对话，body: `{ messages[], context }` |
| `/api/report` | GET | 获取整合报告 Markdown |
| `/api/books` | GET | 获取书籍列表 |

---

## 技术要求

### 组件结构
```
src/
├── views/
│   ├── upload/Upload.vue    # FE-2
│   ├── graph/Graph.vue      # FE-3, FE-4
│   ├── qa/QA.vue           # FE-5
│   ├── chat/Chat.vue       # FE-6
│   └── report/Report.vue    # FE-7
└── App.vue                 # FE-8 三栏布局
```

### 样式
- 纯 CSS（CSS 自定义属性），不用 Tailwind
- 设计方向：简洁专业，适合工具类应用
- 不要用模板样式，要有自己的设计语言

### 依赖
- **AntV G6** — 图谱可视化（`npm install @antv/g6`）
- **marked** — Markdown 渲染（`npm install marked`）

---

## 开发顺序

```
FE-1 → FE-3(mock) → FE-4 → FE-5(mock) → FE-6(mock) → FE-2 → FE-7 → FE-8
```

**策略：先做图谱和问答（核心展示），再做上传，最后整合布局。**

---

## 验收流程

每完成一个任务，在 task-board.md 更新：

```markdown
- [✅ FE-X @前端Agent HH:MM]: 描述
```

---

## 多 Agent 协作规范

### 与后端 Agent（Hermes）协作
- 后端接口未完成时，用 mock 数据先做
- 后端完成后，替换为真实 API 调用
- 接口契约：`docs/api-contract.md` 是唯一依据

### 与调控台（我）协作
- 我负责监控进度，接收你的状态更新
- 遇到阻塞时，告诉我，我协助解决
- 重要决策（如改设计方向）先问我

---

## 禁止事项

- ❌ 不写测试
- ❌ 不安装新依赖（除非是 AntV G6 或 marked）
- ❌ 不做响应式（只适配 1920×1080）
- ❌ 不改 API 契约（接口定义在 docs/api-contract.md）
- ❌ 不写业务逻辑到 API 客户端以外

---

## 开始

按顺序完成任务，每完成一个在 task-board.md 更新状态。遇到问题先自己想办法，实在解决不了叫我。