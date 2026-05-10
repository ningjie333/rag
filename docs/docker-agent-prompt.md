# 容器化部署 Agent 任务提示词

## 任务目标

为"学科知识整合智能体"项目编写 `docker-compose.yml`，实现一键部署前后端服务。

## 技术背景

- **后端**：Python FastAPI，端口 3002，需要 MiniMax API Key（环境变量）
- **前端**：Vue3 + Vite，端口 5173，无状态纯静态
- **向量库**：ChromaDB（内嵌模式，数据持久化到 volume）
- **环境**：需要 Python 3.11+，Node.js 18+

## 交付物

在项目根目录（`scaffold/`）创建：

1. `docker-compose.yml` — 编排文件
2. `Dockerfile.backend` — 后端构建文件
3. `Dockerfile.frontend` — 前端构建文件（或用 nginx）

## 架构要求

```
internet
   │
   ▼
nginx (80/443) ─── 反向代理
   │               ├── /api/* → backend:3002
   │               └── /*     → frontend:5173 (or static)
   │
   ├── frontend:5173 (Vue3 build)
   │     (或直接用 nginx serve dist/)
   │
   └── backend:3002 (FastAPI)
         │
         └── chromadb (volume 持久化)
```

## 关键决策

### 方案 A：前端 dev 模式（简单）
```yaml
services:
  backend:
    build: ./backend
    ports: ["3002:3002"]
    env_file: ./backend/.env
    volumes: ["./data:/app/data"]
  frontend:
    build: ./src
    ports: ["5173:5173"]
    command: npm run dev
```

### 方案 B：前端生产模式（推荐，更正式）
- 前端构建 `npm run build`，nginx serve `dist/`
- 后端用 uvicorn --host 0.0.0.0

## 环境变量处理

`.env` 文件**不**提交到 git，在 docker-compose 里用 `env_file` 或直接写死占位符：
```env
# .env.example（提交）
MINIMAX_API_KEY=your_key_here
```

## 验收标准

1. `docker-compose up --build` 能成功启动
2. 浏览器访问 `http://localhost` 能看到前端
3. API `http://localhost/api/health` 返回 `{"status": "ok"}`
4. `docker-compose down` 能干净停止

## 禁止事项

- ❌ 不在 docker-compose 里硬编码真实 API key
- ❌ 不试图在一个容器里跑前后端（要分离）
- ❌ 不写测试

## 开始

创建 `Dockerfile.backend`、`Dockerfile.frontend`（或 `nginx.conf`）、`docker-compose.yml`。在 task-board.md 记录完成状态。