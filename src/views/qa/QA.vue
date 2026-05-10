<script setup lang="ts">
import { ref } from 'vue'
import { post } from '@/api/client'
import type { Citation, QueryResponse } from '@/types'

const question = ref('')
const loading = ref(false)
const answered = ref(false)
const answerText = ref('')
const citations = ref<Citation[]>([])
const tokenUsage = ref<{ prompt: number; completion: number; total: number } | null>(null)

const mockAnswer: QueryResponse = {
  answer: '心肌炎的诊断主要依据：1) 临床症状（心音混浊、心率加快）2) 心电图检查（ST段抬高、T波倒置）3) 血液检查（肌钙蛋白升高）4) 超声心动图（心室壁运动异常）。治疗方案包括：休息、抗炎治疗、对症支持治疗。',
  citations: [
    { chunk_id: 'c1', text: '心肌炎是指心肌的炎症性疾病，可由感染、自身免疫等因素引起。临床上表现为心音混浊、心率加快、心律不齐等。', source: '兽医诊断学.pdf', page: 128, score: 0.92 },
    { chunk_id: 'c2', text: '心电图检查是诊断心肌炎的重要手段，典型表现为ST段抬高、T波倒置。结合临床症状可初步判断病情严重程度。', source: '兽医诊断学.pdf', page: 130, score: 0.87 },
    { chunk_id: 'c3', text: '肌钙蛋白是心肌损伤的特异性标志物，其升高提示心肌细胞损伤。血液中肌钙蛋白水平与心肌损伤程度呈正相关。', source: '兽医内科学.pdf', page: 56, score: 0.81 },
  ],
  graph_context: {},
}

async function handleSubmit() {
  const q = question.value.trim()
  if (!q || loading.value) return

  loading.value = true
  answered.value = false
  answerText.value = ''
  citations.value = []

  try {
    const res = await post<QueryResponse>('/query', { question: q, top_k: 5 })
    answerText.value = res.answer
    citations.value = res.citations || []
  } catch {
    // Use mock data for UI testing
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
  <div class="qa page fade-in">
    <h1 class="page-title">知识问答</h1>
    <p class="page-subtitle">基于教材知识库的 RAG 检索问答</p>

    <!-- 输入区 -->
    <div class="qa-input card">
      <textarea
        v-model="question"
        class="qa-input__textarea"
        placeholder="输入你的问题，例如：心肌炎的诊断依据有哪些？"
        rows="3"
        @keydown="handleKeydown"
      />
      <div class="qa-input__actions">
        <span class="qa-input__hint">Enter 发送 · Shift+Enter 换行</span>
        <button
          class="btn btn-primary"
          :disabled="!question.trim() || loading"
          @click="handleSubmit"
        >
          <span v-if="loading" class="spin">⏳</span>
          <span v-else>发送</span>
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span class="spin" style="margin-right:8px">⏳</span> 正在检索知识库...
    </div>

    <!-- 回答区域 -->
    <div v-if="answered && !loading" class="qa-result fade-in">
      <!-- AI 回答 -->
      <div class="answer-card card">
        <div class="answer-card__header">
          <span class="answer-card__icon">🤖</span>
          <span class="answer-card__label">AI 回答</span>
        </div>
        <div class="answer-card__content">{{ answerText }}</div>
        <div v-if="tokenUsage" class="answer-card__tokens">
          💬 Token: prompt={{ tokenUsage.prompt.toLocaleString() }} | completion={{ tokenUsage.completion.toLocaleString() }} | 总计={{ tokenUsage.total.toLocaleString() }}
        </div>
      </div>

      <!-- 引用来源 -->
      <div v-if="citations.length > 0" class="citations-section">
        <h2 class="section-title">引用来源</h2>
        <div class="citations-list">
          <div v-for="cite in citations" :key="cite.chunk_id" class="citation-card">
            <div class="citation-card__header">
              <span class="citation-card__source">📄 {{ cite.source }}</span>
              <span class="citation-card__meta">
                第 {{ cite.page }} 页 · 相关度 {{ formatScore(cite.score) }}
              </span>
            </div>
            <p class="citation-card__text">{{ cite.text }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!answered && !loading" class="empty-state">
      <div class="empty-icon">💬</div>
      <div class="empty-text">输入问题开始问答</div>
    </div>
  </div>
</template>

<style scoped>
.qa-input {
  margin-bottom: 24px;
}
.qa-input__textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  transition: border-color var(--transition);
  font-family: inherit;
}
.qa-input__textarea:focus {
  border-color: var(--color-primary);
}
.qa-input__actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
.qa-input__hint {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.answer-card {
  margin-bottom: 24px;
}
.answer-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.answer-card__icon {
  font-size: 20px;
}
.answer-card__label {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}
.answer-card__content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
}
.answer-card__tokens {
  font-size: 11px;
  color: var(--color-text-secondary);
  text-align: right;
  margin-top: 8px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 14px;
}

.citations-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.citation-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius);
  padding: 14px 16px;
  transition: all var(--transition);
}
.citation-card:hover {
  box-shadow: var(--shadow);
}
.citation-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.citation-card__source {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}
.citation-card__meta {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.citation-card__text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}
</style>
