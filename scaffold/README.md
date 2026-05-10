# 学科知识整合智能体

> 生命健康领域 · AI 黑客松项目
> 核心技术：知识图谱 + RAG 问答 + 多教材整合压缩

## 一、Docker 一键启动（推荐）

```bash
git clone https://github.com/ningjie333/rag.git
cd rag
cp .env.example backend/.env
# 编辑 backend/.env 填入你的 MINIMAX_API_KEY
docker-compose up -d --build
# 打开 http://localhost:5173
```

## 二、本地开发启动

```bash
# 0. 环境要求
#    Python 3.12+, Node.js 18+, uv

# 1. 克隆项目
git clone https://github.com/ningjie333/rag.git
cd rag

# 2. 安装前端依赖
npm install

# 3. 安装后端依赖（Python）
cd backend
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 4. 初始化向量库
cd ..
python scripts/init_vector_store.py

# 5. 启动后端（终端 1）
cd backend && uvicorn main:app --reload --port 3002

# 6. 启动前端（终端 2）
npm run dev

# 7. 打开浏览器
#    前端: http://localhost:5173
#    后端: http://localhost:3002/docs (Swagger UI)
#    健康检查: http://localhost:3002/health
```

## 环境变量

在 `backend/` 目录创建 `.env`：

```env
MINIMAX_API_KEY=your_api_key_here
MINIMAX_BASE_URL=https://api.minimax.chat/v1
MINIMAX_MODEL=MiniMax-Text-01
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue3 + Vite + TypeScript | SPA 单页应用 |
| 前端图谱 | AntV G6 | 知识图谱可视化 |
| 后端 | Python FastAPI | REST API |
| 向量库 | ChromaDB | 文本嵌入 + 知识图谱存储 |
| LLM | MiniMax API | 知识点提取 + RAG 生成 |
| PDF 解析 | pymupdf | 教材解析 |
| 分块 | langchain-text-splitters | RecursiveCharacterTextSplitter |

## 目录结构

```
scaffold/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── requirements.txt     # Python 依赖
│   ├── routers/
│   │   ├── upload.py        # POST /api/upload
│   │   ├── query.py         # POST /api/query
│   │   ├── kg.py            # GET/POST /api/graph
│   │   ├── chat.py          # POST /api/chat
│   │   └── books.py         # GET /api/books
│   ├── models/
│   │   └── schemas.py       # Pydantic 模型
│   └── vector_store/
│       ├── chroma_client.py # ChromaDB 客户端
│       ├── pdf_processor.py # PDF 解析 + 分块
│       ├── query_engine.py  # 向量检索
│       └── kg_extractor.py  # LLM 知识点提取
├── src/                     # Vue3 前端
├── docs/
│   └── api-contract.md      # API 契约文档
├── scripts/
│   └── init_vector_store.py # 向量库初始化脚本
└── data/
    └── chroma_db/           # ChromaDB 持久化存储
```

## API 文档

启动后访问 http://localhost:3002/docs 查看 Swagger UI。

---

## 知识图谱 Schema

### 节点 (nodes)

```json
{
  "id": "unique_id",
  "label": "知识点名称",
  "type": "concept | fact | definition",
  "description": "简短描述",
  "source": "来源文件:页码"
}
```

### 边 (edges)

```json
{
  "from": "节点ID",
  "to": "节点ID",
  "relation_type": "prerequisite | contains | associate",
  "weight": 0.0
}
```

### 关系类型说明

| 类型 | 说明 |
|------|------|
| prerequisite | A 是 B 的前置知识 |
| contains | A 包含 B |
| associate | A 与 B 关联 |

---

## 引用与参考

本项目在开发过程中参考了以下开源项目：

| 项目 | 来源 | 参考内容 |
|------|------|----------|
| **jecis-repos/laravel-rag** | GitHub | 4阶段检索管道（语义→关键词→RRF→多跳）+ BM25参数（k1=1.5, b=0.75）+ RRF k=60常数 + 多跳图遍历评分衰减机制 |
| **ChenyuHeee/medical-kg-agent** | GitHub | 7类节点Schema（核心概念/现象/过程/结构/物质/疾病/方法）+ GraphRAG子图注入 + Fixpoint救援机制 |
| **AntV/G6** | GitHub | 图谱可视化节点类型映射 + 频次→半径颜色设计 |
| **ChromaDB** | GitHub | 向量检索 + PersistentClient + 集合管理 |
| **langchain-ai/langchain** | GitHub | RecursiveCharacterTextSplitter 分块策略 |

---

*文档版本：v1.0 | 更新：2026-05-10*
