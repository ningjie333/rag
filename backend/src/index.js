import express from 'express'
import cors from 'cors'
import { initDatabase } from './db/init.js'
import { router as apiRouter } from './routes/index.js'

const app = express()
const PORT = process.env.PORT || 3000

// 中间件
app.use(cors())
app.use(express.json())

// 请求日志（简洁版）
app.use((req, _res, next) => {
  console.log(`${req.method} ${req.path}`)
  next()
})

// 初始化数据库
initDatabase()

// API 路由
app.use('/api', apiRouter)

// 健康检查
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() })
})

// 404
app.use('/api', (_req, res) => {
  res.status(404).json({ error: 'Not found' })
})

// 错误处理
app.use((err, _req, res, _next) => {
  console.error(err)
  res.status(500).json({ error: err.message || 'Internal error' })
})

app.listen(PORT, () => {
  console.log(`🚀 API server running at http://localhost:${PORT}/api`)
})
