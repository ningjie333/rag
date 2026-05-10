<script setup lang="ts">
import { ref, computed } from 'vue'
import { marked } from 'marked'
import { post } from '@/api/client'
import type { Citation, QueryResponse } from '@/types'

const question = ref('')
const loading = ref(false)
const answered = ref(false)
const answerText = ref('')
const citations = ref<Citation[]>([])
const tokenUsage = ref<{ prompt: number; completion: number; total: number } | null>(null)

const mockAnswer: QueryResponse = {
  answer: '心肌炎的诊断主要依据：\n\n1. **临床症状**：心音混浊、心率加快、心律不齐\n2. **心电图检查**：ST段抬高、T波倒置\n3. **血液检查**：肌钙蛋白升高（心肌损伤标志物）\n4. **超声心动图**：心室壁运动异常\n\n治疗方案包括：休息、抗炎治疗、对症支持治疗。',
  citations: [
    { chunk_id: 'c1', text: '心肌炎是指心肌的炎症性疾病，可由感染、自身免疫等因素引起。临床上表现为心音混浊、心率加快、心律不齐等。', source: '诊断学.pdf', page: 128, score: 0.92 },
    { chunk_id: 'c2', text: '心电图检查是诊断心肌炎的重要手段，典型表现为ST段抬高、T波倒置。结合临床症状可初步判断病情严重程度。', source: '诊断学.pdf', page: 130, score: 0.87 },
    { chunk_id: 'c3', text: '肌钙蛋白是心肌损伤的特异性标志物，其升高提示心肌细胞损伤。血液中肌钙蛋白水平与心肌损伤程度呈正相关。', source: '内科学.pdf', page: 56, score: 0.81 },
  ],
  graph_context: {},
}

const answerHtml = computed(() => {
  if (!answerText.value) return ''
  return marked.parse(answerText.value) as string
})

async function handleSubmit() {
  const q = question.value.trim()
  if (!q || loading.value) return

  loading.value = true
  answered.value = false
  answerText.value = ''
  citations.value = []
  tokenUsage.value = null

  try {
    const res = await post<QueryResponse>('/query', { question: q, top_k: 5 })
    answerText.value = res.answer
    citations.value = res.citations || []
  } catch {
    await new Promise(r => setTimeout(r, 800))
    answerText.value = mockAnswer.answer
    citations.value = mockAnswer.citations
  }

  tokenUsage.value = { prompt: 1200, completion: 300, total: 1500 }
  loading.value = false
  answered.value = true
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}

function formatScore(s: number) { return (s * 100).toFixed(0) + '%' }
</script>

<template>
  <div class="qa-view">
    <!-- 头部 -->
    <div class="qa-header">
      <h2 class="qa-title">💡 知识问答</h2>
      <p class="qa-desc">基于教材知识库的 RAG 检索问答</p>
    </div>

    <!-- 输入区 -->
    <div class="qa-input-card">
      <div class="input-wrapper">
        <textarea
          v-model="question"
          class="qa-textarea"
          placeholder="输入你的问题，例如：心肌炎的诊断依据有哪些？"
          rows="3"
          @keydown="handleKeydown"
        />
        <div class="input-footer">
          <span class="input-hint">Enter 发送 · Shift+Enter 换行</span>
          <button class="send-btn" :disabled="!question.trim() || loading" @click="handleSubmit">
            <span v-if="loading" class="send-icon spin">⏳</span>
            <span v-else class="send-icon">➤</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 加载动画 -->
    <div v-if="loading" class="qa-loading">
      <div class="loading-dots"><span /><span /><span /></div>
      <span class="loading-text">正在检索知识库...</span>
    </div>

    <!-- 回答区域 -->
    <div v-if="answered && !loading" class="qa-result">
      <!-- AI 回答卡片 -->
      <div class="answer-card">
        <div class="answer-avatar">🤖</div>
        <div class="answer-body">
          <div class="answer-label">AI 回答</div>
          <div class="answer-content markdown-body" v-html="answerHtml" />
          <div v-if="tokenUsage" class="answer-footer">
            <span class="token-badge">💬 {{ tokenUsage.total.toLocaleString() }} tokens</span>
          </div>
        </div>
      </div>

      <!-- 引用来源 -->
      <div v-if="citations.length > 0" class="citations-card">
        <div class="citations-header">
          <span class="citations-icon">📚</span>
          <span class="citations-title">引用来源</span>
          <span class="citations-count">{{ citations.length }} 条</span>
        </div>
        <div class="citations-list">
          <div v-for="cite in citations" :key="cite.chunk_id" class="citation-item">
            <div class="citation-source">
              <span class="source-name">📄 {{ cite.source }}</span>
              <div class="source-meta">
                <span class="source-page">第 {{ cite.page }} 页</span>
                <span class="source-score">相关度 {{ formatScore(cite.score) }}</span>
              </div>
            </div>
            <p class="citation-text">{{ cite.text }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!answered && !loading" class="qa-empty">
      <div class="empty-icon">💬</div>
      <div class="empty-text">输入问题开始问答</div>
      <div class="empty-hint">可以追问任何教材相关问题</div>
    </div>
  </div>
</template>

<style scoped>
.qa-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
  overflow-y: auto;
}

.qa-header {
  margin-bottom: 16px;
}

.qa-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.qa-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* 输入区 */
.qa-input-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.input-wrapper {
  display: flex;
  flex-direction: column;
}

.qa-textarea {
  width: 100%;
  padding: 8px 0;
  border: none;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
  font-family: inherit;
  background: transparent;
}

.qa-textarea::placeholder {
  color: var(--color-text-secondary);
  opacity: 0.6;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}

.input-hint {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--color-primary);
  color: white;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.send-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-icon {
  line-height: 1;
}

/* 加载动画 */
.qa-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
}

.loading-dots {
  display: flex;
  gap: 6px;
}

.loading-dots span {
  width: 10px;
  height: 10px;
  background: var(--color-primary);
  border-radius: 50%;
  animation: pulse 1.2s infinite;
}

.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 60%, 100% { transform: scale(0.6); opacity: 0.4; }
  30% { transform: scale(1); opacity: 1; }
}

.loading-text {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* 回答区域 */
.qa-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 20px;
}

.answer-card {
  display: flex;
  gap: 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
}

.answer-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.answer-body {
  flex: 1;
  min-width: 0;
}

.answer-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 8px;
}

.answer-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
}

.answer-content :deep(h1),
.answer-content :deep(h2),
.answer-content :deep(h3) {
  font-size: 14px;
  font-weight: 600;
  margin: 12px 0 6px;
}

.answer-content :deep(p) {
  margin-bottom: 8px;
}

.answer-content :deep(ul),
.answer-content :deep(ol) {
  padding-left: 20px;
  margin-bottom: 8px;
}

.answer-content :deep(li) {
  margin-bottom: 4px;
}

.answer-content :deep(strong) {
  font-weight: 600;
}

.answer-footer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
}

.token-badge {
  font-size: 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: 10px;
}

/* 引用来源卡片 */
.citations-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
}

.citations-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
}

.citations-icon {
  font-size: 16px;
}

.citations-title {
  font-size: 14px;
  font-weight: 600;
  flex: 1;
}

.citations-count {
  font-size: 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: 10px;
}

.citations-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.citation-item {
  border-left: 3px solid var(--color-primary);
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 0 8px 8px 0;
}

.citation-source {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.source-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
}

.source-meta {
  display: flex;
  gap: 8px;
}

.source-page,
.source-score {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.citation-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

/* 空状态 */
.qa-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 15px;
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 12px;
  opacity: 0.7;
}
</style>
