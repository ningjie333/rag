# ⚡ 黑客松作战手册

> **5小时生死战。每一分钟都是成本。速度 > 完美，落地 > 优雅。**
> 
> **题材：生命健康 | 平台：桌面端 Web 应用**

---

## 🔑 铁律（不可违反）

| # | 铁律 | 原因 |
|---|------|------|
| 1 | **脚手架 clone 即用** | 不从零搭环境，`git clone scaffold` 直接开干 |
| 2 | **接口契约先行** | 多智能体并行的基础，接口没定就开工等于返工 |
| 3 | **数据模型是枢纽** | 模型一定，前后端数据库全部并行开干 |
| 4 | **时间盒严格限时** | 到点就切，不管做完没做 |
| 5 | **15分钟无进展 → 切Plan B** | 不是只有严重错误才重写，小坑也跳 |
| 6 | **脚本解决一切重复劳动** | 格式/检查/生成全部脚本，人做就是浪费 |

---

## 🏗️ 技术栈（已锁定）

| 层 | 技术 | 说明 |
|---|------|------|
| **前端** | Vue 3 + TypeScript + Vite 6 | Composition API，`<script setup lang="ts">` |
| **后端** | Node.js 24 + Express | ESM 模块，`type: "module"` |
| **数据库** | SQLite（`node:sqlite`） | Node 24 内置，零依赖，零配置 |
| **样式** | 纯 CSS（CSS 自定义属性） | 不用 Tailwind，减少依赖 |
| **部署** | Vercel / Railway | 提前配好账号，`git push` 就上线 |
| **检查** | `_tools/dev/check.py` | 路由/API/空实现检测 |

> **原则：零外部依赖优先。Node 24 内置 SQLite，不需要 better-sqlite3 编译。**

---

## 📁 脚手架位置

```
桌面/hackathon/scaffold/          ← 比赛时 clone 这个
├── index.html
├── package.json                  ← 前端依赖
├── vite.config.ts
├── tsconfig.json
├── check_config.json             ← 代码检查配置
├── .gitignore
├── README.md
├── src/
│   ├── main.ts                   ← 入口（Vue + Pinia + Router）
│   ├── App.vue                   ← 布局（Sidebar + TopBar + RouterView）
│   ├── assets/main.css           ← 全局样式 + CSS 变量
│   ├── api/client.ts             ← 统一 fetch 封装（get/post/put/del）
│   ├── types/index.ts            ← TypeScript 类型定义
│   ├── router/index.ts           ← 路由（2个示例页面）
│   ├── components/
│   │   ├── Sidebar.vue           ← 侧边导航
│   │   ├── TopBar.vue            ← 顶部栏 + 搜索
│   │   ├── EmptyState.vue        ← 空状态
│   │   ├── LoadingSpinner.vue    ← Loading 动画
│   │   ├── StatCard.vue          ← 统计卡片
│   │   ├── PageHeader.vue        ← 页面标题栏
│   │   └── health/               ← 健康领域专用组件
│   │       ├── HealthMetricCard.vue  ← 健康指标卡片
│   │       └── StatusBadge.vue       ← 状态徽章
│   └── views/
│       ├── home/Home.vue         ← 首页（统计 + 快速入口）
│       └── dashboard/Dashboard.vue  ← 数据面板（示例）
└── backend/
    ├── package.json              ← 后端依赖（仅 cors + express）
    ├── src/
    │   ├── index.js              ← 入口（Express + CORS + 路由）
    │   ├── db/init.js            ← 数据库初始化（node:sqlite）
    │   └── routes/index.js       ← API 路由（CRUD 示例）
    └── data/
        ├── schema.sql            ← 数据库结构
        ├── seed.sql              ← 种子数据
        └── health-seed.sql       ← 健康领域参考数据
```

> ✅ 已验证：前端 `vue-tsc --noEmit` 零错误，`vite build` 成功（96KB gzipped）
> ✅ 已验证：后端 `node:sqlite` + express + cors 全部正常

---

## 📐 多智能体分工架构

```
┌─────────────────────────────────────────────────┐
│             🧠 主协调智能体 (Orchestrator)          │
│  职责：定接口、拆任务、派活、集成验证、时间管控       │
│  不写业务代码，只做协调                              │
└──────────┬──────────┬──────────┬──────────────────┘
           │          │          │
    ┌──────▼──┐ ┌─────▼────┐ ┌──▼──────────┐
    │ 前端 Agent│ │ 后端 Agent│ │ 数据库 Agent │
    │ UI+交互   │ │ API+逻辑  │ │ Schema+Seed  │
    └─────────┘ └──────────┘ └─────────────┘
```

### 各智能体职责边界

| 智能体 | 负责 | 不碰 |
|--------|------|------|
| **Orchestrator** | 接口文档、任务拆分、集成验证、时间管控 | 业务代码 |
| **前端 Agent** | 页面组件、路由、状态管理、API 调用层 | 后端业务逻辑、数据库 |
| **后端 Agent** | API 路由、业务逻辑、数据校验 | 页面、CSS、数据库 DDL |
| **数据库 Agent** | Schema 设计、种子数据、索引优化 | 任何应用代码 |

---

## ⏱️ 5小时时间线

```
T+0:00 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ T+5:00
  │         │         │         │         │         │
  ▼         ▼         ▼         ▼         ▼         ▼
 Phase 0    Phase 1    Phase 2    Phase 3    Phase 4    Phase 5
 定题+接口   并行开发    前端冲刺    集成联调    测试修复    部署+路演
 (30min)   (90min)    (60min)    (45min)    (30min)    (15min)
```

### Phase 0：定题 + 接口契约（0:00 - 0:30）

**Orchestrator 执行：**

1. **确定项目主题**（5 min）
   - 一句话说清楚做什么（生命健康领域）
   - 确定核心功能（不超过3个）
   - 命名项目（替换脚手架中的 `projectName`）

2. **设计数据模型**（10 min）
   - 写出核心 Entity 及其字段
   - 确定 Entity 之间的关系
   - **输出：修改 `backend/data/schema.sql`**

3. **定义 API 契约**（10 min）
   - 列出所有 API 端点
   - 每个端点的 Request/Response 结构
   - **输出：`api-contract.md`（前后端对接唯一依据）**

4. **拆任务派活**（5 min）
   - 把任务分配给各 Agent
   - 明确每个 Agent 的交付物

### Phase 1：并行开发（0:30 - 2:00）

**三个 Agent 同时开工：**

#### 数据库 Agent（0:30 - 1:30）
- 修改 `backend/data/schema.sql` 建表
- 修改 `backend/data/seed.sql` 写种子数据
- 验证 CRUD 操作可用
- **交付：** 可连接的数据库 + seed 数据

#### 后端 Agent（0:30 - 2:00）
- 根据 `api-contract.md` 修改 `backend/src/routes/index.js`
- 每个 API 先返回 mock 数据，确保接口通
- 再加业务逻辑
- **交付：** 所有 API 可调用（curl 验证）

#### 前端 Agent（1:00 - 2:00）
- 根据 `api-contract.md` 创建页面组件
- 接入 `src/api/client.ts` 调用后端
- 先用 mock 数据，再替换为真实 API
- **交付：** 所有页面可交互

> **关键：后端必须先用 mock 数据把接口跑通，前端才能接。这是唯一的前后端依赖点。**

### Phase 2：前端冲刺（2:00 - 3:00）

前端 Agent 全力做页面和交互，后端 Agent 继续完善业务逻辑。

**必做项（全部升为必做）：**
- [ ] README.md 填写
- [ ] Seed 数据（5-10条 mock 数据）
- [ ] Logo/品牌（侧边栏改项目名即可）
- [ ] 简单动画（脚手架已有 fade-in / spin）
- [ ] 错误提示（EmptyState 组件已有）

### Phase 3：集成联调（3:00 - 3:45）

**Orchestrator 主导：**

1. 前后端对接验证
2. 核心用户流程跑通
3. 数据库读写验证

**集成检查脚本：**
```bash
# 快速检查
python _tools/dev/check.py --config check_config.json --quick

# 后端冒烟测试
curl -s http://localhost:3000/api/health
curl -s http://localhost:3000/api/items

# 前端类型检查
npx vue-tsc --noEmit
```

### Phase 4：测试 + 修复（3:45 - 4:15）

**只修 CRITICAL 和 HIGH 问题：**
- 🔴 CRITICAL: 核心功能不可用 → 必须修
- 🟡 HIGH: 次要功能异常 → 快速修
- 🟢 MEDIUM/LOW: 不管了

### Phase 5：部署 + 路演（4:15 - 4:30）

```bash
# 构建前端
npm run build

# 部署（提前配好，git push 就上线）
git add -A && git push
```

**路演材料（5分钟准备）：**
- 一句话项目介绍
- 核心功能 Demo 路径
- 技术亮点（1-2个）

---

## 📄 API 契约模板

> **比赛时填写此文件，不超过10分钟。**

```markdown
# API Contract - [项目名称]

## Base URL
`http://localhost:3000/api`

## 认证
无（黑客松不需要认证）

## 端点

### 获取列表
`GET /api/items?page=1&limit=20`
Response: `{ "success": true, "data": [...], "meta": { "total": 10, "page": 1, "limit": 20 } }`

### 获取详情
`GET /api/items/:id`
Response: `{ "success": true, data: {...} }`

### 创建
`POST /api/items`
Body: `{ "name": "xxx" }`
Response: `{ "success": true, "data": { "id": "xxx", "name": "xxx" } }`

### 更新
`PUT /api/items/:id`
Body: `{ "name": "new" }`
Response: `{ "success": true }`

### 删除
`DELETE /api/items/:id`
Response: `204 No Content`
```

---

## 🩺 生命健康领域 - 选题参考

| 方向 | 描述 | 核心数据 |
|------|------|---------|
| **A. 个人健康仪表盘** | 体重/血压/睡眠 → 图表展示 | 健康记录 + 时间序列 |
| **B. 症状自查** | 输入症状 → 可能原因 | 症状-疾病关联 |
| **C. 用药提醒** | 定时提醒 + 进度追踪 | 药物 + 提醒计划 |
| **D. 健康知识库** | 疾病百科 + 科普文章 | 疾病 + 文章内容 |
| **E. 健康数据追踪 + AI 分析** | 数据录入 → 趋势分析 → 建议 | 健康记录 + 参考范围 |

### 领域专用组件（已内置于脚手架）

```
components/health/
├── HealthMetricCard.vue   # 指标卡片（血压/血糖/体重），带状态颜色 + 趋势箭头
└── StatusBadge.vue        # 状态徽章（正常/注意/异常/信息）
```

### 参考种子数据（已内置于脚手架）

```sql
-- backend/data/health-seed.sql
-- 包含：血压、心率、血糖、BMI 的正常/警告/危险范围
```

---

## 🚫 禁止事项

| 禁止 | 原因 |
|------|------|
| ❌ 现场选技术栈 | 已锁定，不讨论 |
| ❌ 从零搭环境 | clone scaffold 直接用 |
| ❌ 写单元测试 | 5小时不写测试 |
| ❌ 做响应式适配 | 只适配桌面端 |
| ❌ 做用户认证 | 用 mock 用户 |
| ❌ 做权限管理 | 不存在的 |
| ❌ 做日志/监控 | console.log 够了 |
| ❌ 纠结命名/格式 | check.py 一把梭 |
| ❌ 修 bug 超过15分钟 | 切 Plan B |
| ❌ 新增 npm 依赖 | 除非绝对必要 |

---

## 🔧 常用命令速查

```bash
# ===== 前端 =====
cd scaffold
npm install              # 首次安装依赖
npm run dev              # 启动开发服务器 → http://localhost:5173
npm run build            # 构建 → dist/
npx vue-tsc --noEmit     # 类型检查

# ===== 后端 =====
cd scaffold/backend
npm install              # 首次安装依赖
node src/index.js         # 启动 API 服务器 → http://localhost:3000/api

# ===== 数据库 =====
# 数据库在 backend/data/app.db，后端启动时自动初始化
# 修改 schema.sql 或 seed.sql 后重启后端即可

# ===== 检查 =====
python _tools/dev/check.py --config check_config.json --quick

# ===== 验证 =====
curl http://localhost:3000/api/health
curl http://localhost:3000/api/items
```

---

## 🚨 Plan B 降级策略

```
完整版 → mock 数据版 → 静态展示版 → 截图假装版
```

| 情况 | Plan B |
|------|--------|
| 后端 API 超时 | 前端用 mock 数据 |
| 数据库连不上 | 用内存数组 |
| 前端页面做不完 | 静态 HTML，按钮不响应也行 |
| 部署失败 | 本地跑，投屏演示 |
| 功能做不出来 | 砍掉，缩小 MVP |

---

## ✅ Phase 验收清单

### Phase 0
- [ ] 项目主题一句话
- [ ] schema.sql 有完整表结构
- [ ] api-contract.md 有所有端点
- [ ] 任务已分配

### Phase 1
- [ ] 数据库可连接，seed 数据已导入
- [ ] 所有 API 可调用
- [ ] 前端页面骨架完成

### Phase 2
- [ ] 所有页面有内容
- [ ] 核心交互可走通
- [ ] 必做项全部完成（README/Seed/Logo/动画/错误提示）

### Phase 3
- [ ] 前后端对接完成
- [ ] 核心流程端到端跑通
- [ ] 类型检查通过

### Phase 4
- [ ] 无 CRITICAL 问题

### Phase 5
- [ ] 已部署，公网可访问
- [ ] 有 Demo 路径

---

## 🧠 给各 Agent 的提示词模板

### 派活给前端 Agent
```
你是一个黑客松前端开发 Agent。

## 项目
[一句话描述]

## 技术栈
Vue 3 + TypeScript + Vite，纯 CSS（不用 Tailwind）

## 已有脚手架
- src/api/client.ts：统一 fetch 封装（get/post/put/del）
- src/components/：Sidebar/TopBar/EmptyState/LoadingSpinner/StatCard/PageHeader
- src/components/health/：HealthMetricCard/StatusBadge（健康领域组件）
- src/router/index.ts：路由配置
- src/types/index.ts：类型定义

## 任务清单（来自 task-board.md）
| 任务ID | 描述 | 验收标准 |
|--------|------|----------|
| FE-1 | 创建 [页面名] 页面 | 访问 `/[route]` 能看到页面，内容可读 |
| FE-2 | 接入 GET /api/[entity] 列表 | 页面加载后显示后端数据，无 console.error |
| FE-3 | 接入 POST /api/[entity] 创建 | 表单提交后数据出现在列表中 |
| FE-4 | [其他任务] | [验收标准] |

## API 契约
参考 `scaffold/docs/api-contract.md`，关键端点：
- GET /api/[entity] → { success, data[], meta{} }
- POST /api/[entity] → { success, data{} }

## 你的交付物
1. `src/views/` 下创建 [页面名].vue
2. `src/router/index.ts` 添加路由
3. `src/components/Sidebar.vue` 添加菜单项
4. `src/api/client.ts` 接入后端 API
5. `src/App.vue` 修改 projectName

## 验收流程
每完成一个任务，在 task-board.md 中更新：
```
- [✅ FE-1 @前端Agent 09:15]: 描述
```

## 时间
60 分钟。先做核心功能（FE-1 → FE-2 → FE-3）。

## 禁止
- 不写测试
- 不安装新依赖
- 不纠结样式
- 不做响应式

开始干活。
```

### 派活给后端 Agent
```
你是一个黑客松后端开发 Agent。

## 项目
[一句话描述]

## 技术栈
Node.js 24 + Express + node:sqlite（零外部数据库依赖）

## 已有脚手架
- backend/src/index.js：Express 入口
- backend/src/db/init.js：数据库初始化（node:sqlite）
- backend/src/routes/index.js：API 路由（有 CRUD 示例）
- backend/data/schema.sql：数据库结构
- backend/data/seed.sql：种子数据

## 任务清单（来自 task-board.md）
| 任务ID | 描述 | 验收标准 |
|--------|------|----------|
| BE-1 | GET /api/[entity] 列表 | curl 返回 { success, data[], meta{} } |
| BE-2 | GET /api/[entity]/:id 详情 | curl 返回 { success, data{} } |
| BE-3 | POST /api/[entity] 创建 | curl -X POST 返回 { success, data{} } |
| BE-4 | PUT /api/[entity]/:id 更新 | curl -X PUT 返回 { success } |
| BE-5 | DELETE /api/[entity]/:id 删除 | curl -X DELETE 返回 204 |

## 依赖关系
- BE-1 依赖: DB-2（数据库表和种子数据就绪）
- BE-2, BE-4, BE-5 依赖: BE-1
- BE-3 依赖: BE-1

## 关键规则
1. 每个 API 先用 mock 数据跑通（返回假数据），再接真实数据库
2. Response 格式必须符合 api-contract.md 规范
3. 用 `console.log` 调试，启动命令: `cd scaffold/backend && node src/index.js`

## 交付物
1. `backend/data/schema.sql` - CREATE TABLE 语句
2. `backend/data/seed.sql` - INSERT mock 数据
3. `backend/src/routes/index.js` - 所有 API 实现

## 验收流程
每完成一个 API，在 task-board.md 中更新：
```
- [✅ BE-1 @后端Agent 09:30]: GET /api/[entity] 列表 ✓
```
然后用 curl 验证：
```bash
curl -s http://localhost:3000/api/[entity] | jq .
```

## 时间
90 分钟。前 30 分钟让所有 API 用 mock 数据跑通，后 60 分钟接真实数据库。

## 禁止
- 不写测试
- 不安装新 npm 包
- 不做认证/权限

开始干活。
```

### 派活给数据库 Agent
```
你是一个黑客松数据库 Agent。

## 项目
[一句话描述]

## 数据模型（参考 api-contract.md）
[Entity 描述]

## 任务清单（来自 task-board.md）
| 任务ID | 描述 | 验收标准 |
|--------|------|----------|
| DB-1 | 创建 [表名] 表 | schema.sql 中有 CREATE TABLE 语句 |
| DB-2 | 插入 [N] 条种子数据 | seed.sql 中有 INSERT 语句，可读 |
| DB-3 | [可选] 创建索引 | schema.sql 中有 CREATE INDEX |

## 交付物
1. `backend/data/schema.sql` - 完整 CREATE TABLE（字段、约束、索引）
2. `backend/data/seed.sql` - 5-10 条真实感数据

## 数据要求
- 种子数据要真实（不是 "test1", "test2"）
- 有中文内容（生命健康领域）
- 足够测试各种场景

## 验收流程
完成后在 task-board.md 中更新：
```
- [✅ DB-1 @数据库Agent 09:05]: 创建 [表名] 表 ✓
- [✅ DB-2 @数据库Agent 09:12]: 插入种子数据 8 条 ✓
```

## 时间
60 分钟。

开始干活。
```

---

> **📌 脚手架位置：`Desktop/hackathon/scaffold/`**
> **📌 比赛开始时：clone scaffold → Phase 0 照着做 → 不需要思考，只需要执行。**
