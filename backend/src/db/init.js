import { DatabaseSync } from 'node:sqlite'
import { readFileSync, existsSync, mkdirSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DB_DIR = join(__dirname, '../../data')
const DB_PATH = join(DB_DIR, 'app.db')
const SCHEMA_PATH = join(__dirname, '../../data/schema.sql')
const SEED_PATH = join(__dirname, '../../data/seed.sql')

// 确保数据目录存在
if (!existsSync(DB_DIR)) mkdirSync(DB_DIR, { recursive: true })

// 创建数据库连接（Node 24 内置 SQLite）
const db = new DatabaseSync(DB_PATH)

// 开启 WAL 模式提升性能
db.exec('PRAGMA journal_mode = WAL')
db.exec('PRAGMA foreign_keys = ON')

export function initDatabase() {
  // 建表
  if (existsSync(SCHEMA_PATH)) {
    const schema = readFileSync(SCHEMA_PATH, 'utf-8')
    // 分割 SQL 语句逐条执行（跳过注释和空行）
    const statements = schema
      .split(';')
      .map(s => s.trim())
      .filter(s => s && !s.startsWith('--'))
    for (const sql of statements) {
      try {
        db.exec(sql)
      } catch (e) {
        if (!e.message.includes('already exists')) console.warn('Schema:', e.message)
      }
    }
    console.log('✅ Database schema initialized')
  }

  // 导入种子数据
  if (existsSync(SEED_PATH)) {
    const seed = readFileSync(SEED_PATH, 'utf-8')
    const statements = seed
      .split(';')
      .map(s => s.trim())
      .filter(s => s && !s.startsWith('--'))
    for (const sql of statements) {
      try {
        db.exec(sql)
      } catch (e) {
        if (!e.message.includes('already exists')) console.warn('Seed:', e.message)
      }
    }
    console.log('✅ Seed data loaded')
  }
}

export default db
