# 任务看板 — 学科知识整合智能体

> 项目: AI 全栈极速黑客松：学科知识整合智能体
> 开始时间: T+0:00
> 调控台: Claude Code（只做任务分配/验收/联调，不写业务代码）

---

## 📋 Phase 0 ~ Phase 5 任务池

### 🗄️ 数据/基础设施 Agent

| 任务ID | 描述 | 验收标准 | 依赖 | 状态 |
|--------|------|----------|------|------|
| DB-1 | 设计知识图谱 Schema（nodes/edges 表） | `backend/schema.sql` 有 CREATE TABLE | 无 | ⏳ |
| DB-2 | 准备 mock 教材数据（5条知识点） | seed.sql 可用，API 能返回数据 | DB-1 | ⏳ |
| DB-3 | 向量库目录初始化 | `backend/vector_store/` 目录存在 | DB-2 | ⏳ |
| DB-4 | 配置 .env（OPENAI_API_KEY 等） | 后端启动不报 env 错误 | 无 | ⏳ |

### 🔧 后端 Agent（Python FastAPI）

| 任务ID | 描述 | 验收标准 | 依赖 | 状态 |
|--------|------|----------|------|------|
| BE-1 | FastAPI 项目骨架 + CORS | `curl localhost:8000/docs` 返回 Swagger UI | DB-4 | ⏳ |
| BE-2 | 文档解析接口 POST `/api/upload` | 上传 PDF/TXT 返回结构化 JSON | DB-1 | ⏳ |
| BE-3 | 知识图谱构建接口 POST `/api/graph/build` | 返回 `{ nodes: [], edges: [] }` | BE-2 | ⏳ |
| BE-4 | 跨教材整合接口 POST `/api/graph/merge` | 返回压缩统计 `{ ratio: 0.28 }` | BE-3 | ⏳ |
| BE-5 | RAG 问答接口 POST `/api/qa` | 返回 `{ answer, sources[] }` 带引用 | DB-3 | ⏳ |
| BE-6 | 多轮对话接口 POST `/api/chat` | 返回回答 + 保存历史 | BE-5 | ⏳ |
| BE-7 | 整合报告生成 GET `/api/report` | 返回 Markdown 格式报告 | BE-4 | ⏳ |

### 🎨 前端 Agent（Vue3）

| 任务ID | 描述 | 验收标准 | 依赖 | 状态 |
|--------|------|----------|------|------|
| FE-1 | Vue3 SPA 骨架 + 路由 | `http://localhost:5173` 能访问 | 无 | ⏳ |
| FE-2 | 教材上传组件（拖拽 + 解析状态） | 上传 PDF 显示文件名 + 进度条 | BE-2 mock | ✅ |
| FE-3 | 图谱可视化（AntV G6） | 显示节点+边，缩放/拖拽/点击 | BE-3 mock | ⏳ |
| FE-4 | 图谱交互（节点详情/颜色映射） | 点击节点弹详情，频次→颜色 | FE-3 | ⏳ |
| FE-5 | RAG 问答界面 | 提问显示回答 + 引用来源列表 | BE-5 mock | ✅ |
| FE-6 | 多轮对话界面 | 对话历史可见，可继续追问 | BE-6 mock | ✅ |
| FE-7 | 报告预览/下载 | 能预览 Markdown，可下载 | BE-7 mock | ⏳ |
| FE-8 | SPA 布局（1920×1080 三栏） | 左侧教材管理/中间图谱/右侧Tab | FE-2~7 | ⏳ |

### 📝 文档 Agent

| 任务ID | 描述 | 验收标准 | 依赖 | 状态 |
|--------|------|----------|------|------|
| DOC-1 | `README.md` | 项目介绍 + 快速启动 + 技术栈 | BE-1 | ⏳ |
| DOC-2 | `docs/Agent架构说明.md` | Mermaid 架构图 + 设计决策 | BE-3 | ⏳ |
| DOC-3 | `docs/需求分析.md` | 功能列表 + 用户场景 | FE-2 | ⏳ |
| DOC-4 | `docs/系统设计.md` | 架构图 + 模块说明 + 接口清单 | BE-7 | ⏳ |
| DOC-5 | `docs/整合报告.md` | 系统自动生成 + 人工润色 | BE-4+BE-6 | ⏳ |

---

## 🔗 依赖关系图

```
DB-1 ──► BE-2 ──► BE-3 ──┬──► BE-4 ──► BE-7 ──► DOC-4 ──► DOC-5
                         │                          ▲
                         │                          │
                         └──► BE-5 ──► BE-6 ──► FE-6
                            ▲                       ▲
                            │                       │
                         DB-3                       │
                            │                       │
FE-1 ──► FE-2 ──► FE-3 ───┴────────────────────────┘
   ▲          ▲
   │          └────────── FE-4 ──► FE-5 ──► FE-7 ──► FE-8
   │
FE-8 ◄─────────────────────────────────────────────────┘
```

---

## ⏱️ 阶段时间线

| 阶段 | 时间 | 目标 |
|------|------|------|
| Phase 0 | T+0:00 ~ T+0:30 | 架子搭好，前后端通 |
| Phase 1 | T+0:30 ~ T+2:00 | 核心功能并行开发 |
| Phase 2 | T+2:00 ~ T+3:30 | 前后端对接 + 图谱调通 |
| Phase 3 | T+3:30 ~ T+4:15 | 文档编写 |
| Phase 4 | T+4:15 ~ T+4:45 | 部署 + 自查 |
| Phase 5 | T+4:45 ~ T+5:00 | 收尾 + 提交 |

---

- [✅ FE-7 @11:15]: 报告预览/下载完成（marked 渲染 + 下载功能）
- [✅ FE-8 @11:15]: 三栏布局完成（240px | auto | 320px）

## ✅ 已完成

- [✅ FE-2 @2026]: 教材上传组件完成（拖拽+进度条+历史列表）
- [✅ FE-5 @2026]: RAG 问答界面完成（提问+回答+引用来源）
- [✅ FE-6 @2026]: 多轮对话界面完成（消息气泡+历史+输入）

### Phase 0 完成 ✅（T+0:05）
- FastAPI 项目结构（main.py + 5个路由 + Pydantic schemas）
- API Contract 更新（8个端点）
- README 更新（快速启动 + 目录结构 + Schema 说明）
- 端口：后端 3002，前端 5173

### Phase 1 进行中 — Hermes 进度 ✅

| 文件 | 功能 | 参考 |
|------|------|------|
| `vector_store/kg_extractor.py` | LLM 知识点提取（prompt 增强）| Tutor ConceptExtractionService.cs |
| `vector_store/relation_inferrer.py` | 关系推理 + 去环 + 去重 | Tutor ConceptCorrelationService.cs |
| `routers/kg.py` | 图谱查询/构建/合并接口 | 集成上述模块 |
| `routers/upload.py` | PDF/TXT 上传解析入库 | 接入 pdf_processor + chromadb |

**relation_inferrer.py 核心功能：**
- `infer_all_relations()` — 多信号关联 + LLM 推理
- `remove_cycles()` — DFS 去环
- `merge_duplicate_concepts()` — 同名合并

**API 端点：**
- `POST /upload` — 上传 PDF/TXT，解析分块存 ChromaDB ✅ (BE-2)
- `GET /graph` — 获取图谱 ✅
- `POST /graph/build` — 构建图谱 ✅ (BE-3)
- `POST /graph/merge` — 跨教材整合 ✅ (BE-4)
- `POST /query` — RAG 检索问答 ✅ (BE-5)
- `POST /chat` — 多轮对话 ✅ (BE-6)
- `GET /books` — 书籍列表 ✅
- `GET /report` — 整合报告生成 ✅ (BE-7)

**所有后端 API 已完成！**

---

- [✅ FE-3 @T+0:XX]: 图谱可视化完成（AntV G6 + mock 数据）
- [✅ FE-4 @T+0:XX]: 图谱交互完成（节点详情面板/颜色映射/频次大小/缩放控制）

### 当前阻塞 & 进行中

| 任务 | 状态 | 说明 |
|------|------|------|
| BE-1~BE-7 | ✅ **全部完成** | 后端 API 已就绪 |
| FE-1~FE-8 | ✅ **全部完成** | 前端 8 个任务已全部完成 |
| DOC-1~DOC-5 | ⏳ 待分配 | 文档 Agent |
| DOC-2 (Agent架构) | ✅ 完成 | `docs/Agent架构说明.md` 已写 |

---

## 🎨 前端 Agent 任务分配

### 前端 Agent 提示词
- 位置：`docs/frontend-agent-prompt.md`
- 开发顺序：FE-1 → FE-3(mock) → FE-4 → FE-5(mock) → FE-6(mock) → FE-2 → FE-7 → FE-8
- 技术栈：Vue 3 + TypeScript + AntV G6 + marked

### 状态更新格式
每完成一个任务，在「当前阻塞 & 进行中」区域更新：
```markdown
| FE-X | ✅ 完成 @HH:MM | 描述 |
```

---

## 🚨 阻塞 & 切换 Plan B 记录

| 时间 | 问题 | 决定 | 切换 |
|------|------|------|------|

---

## 🎯 P1 加分项 Agent

| 任务ID | 描述 | 提示词文件 | 状态 |
|--------|------|----------|------|
| P1-DOCKER | docker-compose.yml + Dockerfile | `docs/docker-agent-prompt.md` | ⏳ |
| P1-PDF | PDF 报告导出 | `docs/pdf-export-agent-prompt.md` | ⏳ |
| P1-TOKEN | Token 消耗可视化 | `docs/token-viz-agent-prompt.md` | ⏳ |
| P1-DOCS | 需求分析/系统设计/整合报告 | `docs/docs-agent-prompt.md` | ⏳ |

---

## 📝 笔记

（调控台随时记录关键决策）