export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
}

export interface Pagination {
  page: number
  limit: number
  total: number
}

export interface BaseEntity {
  id: string
  created_at: string
  updated_at: string
}

export interface KGNode {
  id: string
  label: string
  type: 'concept' | 'fact' | 'definition'
  description: string
  source: string
  frequency?: number
}

export interface KGEdge {
  from_node: string
  to_node: string
  relation_type: 'prerequisite' | 'contains' | 'associate'
  weight: number
}

export interface GraphData {
  nodes: KGNode[]
  edges: KGEdge[]
  total_nodes: number
  total_edges: number
}

export interface Citation {
  chunk_id: string
  text: string
  source: string
  page: number
  score: number
}

export interface QueryRequest {
  question: string
  top_k?: number
}

export interface QueryResponse {
  answer: string
  citations: Citation[]
  graph_context: Record<string, unknown>
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatContext {
  book_titles?: string[]
}

export interface ChatRequest {
  messages: ChatMessage[]
  context?: ChatContext
}

export interface ChatResponse {
  reply: string
  citations: Citation[]
  graph_snapshot?: GraphData
}

export interface UploadResponse {
  success: boolean
  chunks: number
  message: string
  book_title: string
}

export interface BookInfo {
  title: string
  chunk_count: number
  created_at: string
}
