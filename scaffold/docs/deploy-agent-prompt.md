# Deploy Agent Prompt

> 项目：学科知识整合智能体
> 任务：docker-compose 加 health check + 本地分离启动脚本

## 现状

已有

- `docker-compose.yml` — 基本编排（backend + frontend）
- `Dockerfile.backend` — Python 3.11 slim
- `Dockerfile.frontend` — Node 18 build + nginx serve

问题

- 没有 health check 探针
- docker 环境有时不可用，需要支持本地分离启动

## 任务清单

### T-DEPLOY-1：加 health check 探针

修改 `docker-compose.yml`，为 backend 加：

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3002/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

> 注：frontend 用 nginx 无健康检查端点，改用 `curl` 依赖。

### T-DEPLOY-2：加本地开发 override

创建 `docker-compose.override.yml`：

```yaml
services:
  backend:
    volumes:
      - ./backend:/app/backend
    command: uvicorn main:app --host 0.0.0.0 --port 3002 --reload

  frontend:
    volumes:
      - ./src:/app/src
    command: npm run dev -- --host 0.0.0.0
    ports:
      - "5173:5173"
```

### T-DEPLOY-3：前后端分离启动脚本

创建 `scripts/start_backend.sh`：

```bash
#!/bin/bash
cd "$(dirname "$0")/.."
source backend/.venv/bin/activate 2>/dev/null || source backend/.venv/Scripts/activate 2>/dev/null
cd backend
uvicorn main:app --host 0.0.0.0 --port 3002
```

创建 `scripts/start_frontend.sh`：

```bash
#!/bin/bash
cd "$(dirname "$0")/.."
npm run dev
```

赋予执行权限（Windows 下 Git Bash 或 WSL 可用 `chmod +x`）。

### T-DEPLOY-4：验证

```bash
# Health check
docker-compose ps  # 确认 healthy

# 本地分离启动
./scripts/start_backend.sh &
# 确认 http://localhost:3002/health 返回 {"status":"ok"...}

./scripts/start_frontend.sh &
# 确认 http://localhost:5173 可访问
```

## 交付物

1. 修改后的 `docker-compose.yml`（加 health check）
2. 新建 `docker-compose.override.yml`
3. 新建 `scripts/start_backend.sh`
4. 新建 `scripts/start_frontend.sh`
5. 在 task-board.md 更新状态

## 验收标准

- `docker-compose ps` 显示 `healthy`
- `docker-compose exec backend curl http://localhost:3002/health` 返回 `{"status":"ok"...}`
- `docker-compose up -d` 能正常启动两个容器
- `./scripts/start_backend.sh` 能以后端 3002 启动
- `./scripts/start_frontend.sh` 能以前端 5173 启动

## 注意

- health check 必须真实可工作
- 不要改端口映射（3002 和 80）
- .env.example 要包含所有需要的变量（OPENAI_API_KEY 等）
