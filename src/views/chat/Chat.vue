<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { post } from '@/api/client'
import type { ChatMessage, Citation, ChatResponse } from '@/types'

interface DisplayMessage extends ChatMessage {
  citations?: Citation[]
  tokenUsage?: { prompt: number; completion: number; total: number }
}

const messages = ref<DisplayMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const mockCitations: Citation[] = [
  { chunk_id: 'c1', text: '心肌炎是指心肌的炎症性疾病，可由感染、自身免疫等因素引起。', source: '兽医诊断学.pdf', page: 128, score: 0.92 },
  { chunk_id: 'c2', text: '心电图检查是诊断心肌炎的重要手段，典型表现为ST段抬高。', source: '兽医诊断学.pdf', page: 130, score: 0.87 },
]

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  await scrollToBottom()

  const chatMsgs: ChatMessage[] = messages.value.map(m => ({ role: m.role, content: m.content }))

  try {
    const res = await post<ChatResponse>('/chat', { messages: chatMsgs, context: {} })
    messages.value.push({
      role: 'assistant',
      content: res.reply,
      citations: res.citations || [],
      tokenUsage: { prompt: 1200, completion: 300, total: 1500 },
    })
  } catch {
    // Mock response for UI testing
    await new Promise(r => setTimeout(r, 600))
    const lastUserMsg = messages.value[messages.value.length - 1].content
    messages.value.push({
      role: 'assistant',
      content: `关于"${lastUserMsg}"，根据教材知识库检索结果：\n\n1. 该知识点在兽医诊断学中有详细阐述\n2. 涉及相关的基础理论和临床应用\n3. 建议结合图谱查看相关概念之间的关联\n\n如需进一步追问，请继续提问。`,
      citations: mockCitations,
      tokenUsage: { prompt: 1200, completion: 300, total: 1500 },
    })
  }

  loading.value = false
  await scrollToBottom()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function newChat() {
  messages.value = []
}

function formatScore(s: number) { return (s * 100).toFixed(0) + '%' }
</script>

<template>
  <div class="chat page fade-in">
    <div class="chat__header">
      <div>
        <h1 class="page-title">多轮对话</h1>
        <p class="page-subtitle">基于知识图谱的多轮追问对话</p>
      </div>
      <button class="btn btn-outline btn-sm" @click="newChat">
        🔄 新对话
      </button>
    </div>

    <div class="chat__layout">
      <!-- 对话历史 -->
      <div ref="chatContainer" class="chat__messages">
        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">💬</div>
          <div class="empty-text">开始对话吧，可以追问任何教材相关问题</div>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" class="message-row" :class="'message-row--' + msg.role">
          <div class="message-bubble" :class="'message-bubble--' + msg.role">
            <!-- 用户消息 -->
            <template v-if="msg.role === 'user'">
              <div class="message-bubble__text">{{ msg.content }}</div>
            </template>

            <!-- AI 消息 -->
            <template v-else>
              <div class="message-bubble__text">{{ msg.content }}</div>

              <!-- 引用来源 -->
              <div v-if="msg.citations && msg.citations.length > 0" class="message-citations">
                <div class="message-citations__title">📚 引用来源</div>
                <div
                  v-for="cite in msg.citations"
                  :key="cite.chunk_id"
                  class="citation-mini"
                >
                  <div class="citation-mini__header">
                    <span class="citation-mini__source">{{ cite.source }} · 第{{ cite.page }}页</span>
                    <span class="citation-mini__score">{{ formatScore(cite.score) }}</span>
                  </div>
                  <p class="citation-mini__text">{{ cite.text }}</p>
                </div>
              </div>

              <!-- Token 统计 -->
              <div v-if="msg.tokenUsage" class="message-tokens">
                💬 Token: prompt={{ msg.tokenUsage.prompt.toLocaleString() }} | completion={{ msg.tokenUsage.completion.toLocaleString() }} | 总计={{ msg.tokenUsage.total.toLocaleString() }}
              </div>
            </template>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="message-row message-row--assistant">
          <div class="message-bubble message-bubble--assistant">
            <div class="typing-indicator">
              <span /><span /><span />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入 -->
      <div class="chat__input card">
        <textarea
          v-model="inputText"
          class="chat__textarea"
          placeholder="输入问题... Enter 发送，Shift+Enter 换行"
          rows="2"
          @keydown="handleKeydown"
        />
        <button
          class="btn btn-primary"
          :disabled="!inputText.trim() || loading"
          @click="handleSend"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--topbar-height) - 48px);
  padding-bottom: 0;
}
.chat__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.chat__header .page-subtitle {
  margin-bottom: 0;
}

.chat__layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat__messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-row {
  display: flex;
}
.message-row--user {
  justify-content: flex-end;
}
.message-row--assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
}
.message-bubble--user {
  background: var(--color-primary);
  color: white;
  border-bottom-right-radius: 4px;
}
.message-bubble--assistant {
  background: #f1f5f9;
  color: var(--color-text);
  border-bottom-left-radius: 4px;
}
.message-bubble__text {
  white-space: pre-wrap;
}

.message-citations {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}
.message-citations__title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.citation-mini {
  background: white;
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-primary);
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 6px;
}
.citation-mini:last-child {
  margin-bottom: 0;
}
.citation-mini__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.citation-mini__source {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
}
.citation-mini__score {
  font-size: 11px;
  color: var(--color-text-secondary);
}
.citation-mini__text {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.message-tokens {
  font-size: 11px;
  color: var(--color-text-secondary);
  text-align: right;
  margin-top: 6px;
}

/* 输入区域 */
.chat__input {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding: 14px 16px;
  margin-top: 12px;
  flex-shrink: 0;
}
.chat__textarea {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  transition: border-color var(--transition);
  font-family: inherit;
}
.chat__textarea:focus {
  border-color: var(--color-primary);
}

/* 打字动画 */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #94a3b8;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}
</style>
