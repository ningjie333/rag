/**
 * 全局类型定义
 *
 * 比赛时根据实际业务修改这里的类型。
 * 规则：所有跨组件共享的类型定义在这里，单组件内部类型放在组件文件内。
 */

// ===== API 通用响应 =====
export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
  meta?: {
    total: number
    page: number
    limit: number
  }
}

// ===== 分页 =====
export interface Pagination {
  page: number
  limit: number
  total: number
}

// ===== 通用实体基类 =====
export interface BaseEntity {
  id: string
  created_at: string
  updated_at: string
}

// ===== 👇 在这里添加你的业务类型 =====
// 示例：
// export interface Item extends BaseEntity {
//   name: string
//   description: string
//   status: 'active' | 'inactive'
//   tags: string[]
// }
