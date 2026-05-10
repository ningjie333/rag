<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import { post } from '@/api/client'
import type { ChatMessage, Citation, ChatResponse } from '@/types'

interface DisplayMessage extends ChatMessage {
  citations?: Citation[]
  tokenUsage?: { prompt: number; completion: number; total: number }
}

interface FeedbackOption {
  label: string
  action: string
  input?: boolean
}

const messages = ref<DisplayMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const activeFeedbackMsgIdx = ref<number | null>(null)
const feedbackInput = ref('')
const feedbackInputPrompt = ref('')
const feedbackLoading = ref(false)
const feedbackSuccess = ref<number | null>(null)
const feedbackInputRef = ref<HTMLInputElement | null>(null)

const mockCitations: Citation[] = [
  { chunk_id: 'c1', text: '心肌炎是指心肌的炎症性疾病，可由感染、自身免疫等因素引起。', source: '诊断学.pdf', page: 128, score: 0.92 },
  { chunk_id: 'c2', text: '心电图检查是诊断心肌炎的重要手段，典型表现为ST段抬高。', source: '诊断学.pdf', page: 130, score: 0.87 },
]

const positiveOptions: FeedbackOption[] = [
  { label: '关系正确', action: 'correct_relation' },
  { label: '信息准确', action: 'confirm_accurate' },
]

const negativeOptions: FeedbackOption[] = [
  { label: '关系有误', action: 'incorrect_relation' },
  { label: '描述不准确', action: 'update_node', input: true },
  { label: '缺少关系', action: 'new_relation', input: true },
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
    await new Promise(r => setTimeout(r, 600))
    const lastUserMsg = messages.value[messages.value.length - 1].content
    messages.value.push({
      role: 'assistant',
      content: `关于"${lastUserMsg}"，根据教材知识库检索结果：\n\n1. 该知识点在诊断学中有详细阐述\n2. 涉及相关的基础理论和临床应用\n3. 建议结合图谱查看相关概念之间的关联\n\n如需进一步追问，请继续提问。`,
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

function renderMarkdown(text: string) {
  return marked.parse(text) as string
}

function toggleFeedbackPanel(msgIdx: number) {
  if (activeFeedbackMsgIdx.value === msgIdx) {
    activeFeedbackMsgIdx.value = null
    feedbackInput.value = ''
    feedbackInputPrompt.value = ''
  } else {
    activeFeedbackMsgIdx.value = msgIdx
    feedbackInput.value = ''
    feedbackInputPrompt.value = ''
  }
}

function closeFeedbackPanel() {
  activeFeedbackMsgIdx.value = null
  feedbackInput.value = ''
  feedbackInputPrompt.value = ''
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.feedback-panel') && !target.closest('.feedback-btn')) {
    closeFeedbackPanel()
  }
}

async function submitFeedback(msgIdx: number, action: string) {
  const msg = messages.value[msgIdx]
  feedbackLoading.value = true

  const payload: Record<string, unknown> = { feedback_type: action }

  if (action === 'confirm_accurate') {
    payload.feedback_type = 'update_node'
    payload.content = '确认准确'
    if (msg.citations && msg.citations.length > 0) {
      payload.node_id = msg.citations[0].chunk_id
    }
  } else if (action === 'correct_relation' || action === 'incorrect_relation') {
    if (msg.citations && msg.citations.length > 0) {
      payload.relation_from = msg.citations[0].chunk_id
      if (msg.citations.length > 1) {
        payload.relation_to = msg.citations[1].chunk_id
      }
    }
  }

  try {
    await post('/feedback', payload)
  } catch { /* mock success */ }

  feedbackSuccess.value = msgIdx
  activeFeedbackMsgIdx.value = null
  feedbackLoading.value = false
  setTimeout(() => {
    if (feedbackSuccess.value === msgIdx) feedbackSuccess.value = null
  }, 2000)
}

function promptForInput(msgIdx: number, action: string, prompt: string) {
  feedbackInput.value = ''
  feedbackInputPrompt.value = prompt
  activeFeedbackMsgIdx.value = msgIdx
  nextTick(() => feedbackInputRef.value?.focus())
}

function cancelInput() {
  feedbackInput.value = ''
  feedbackInputPrompt.value = ''
}

function submitWithInput(msgIdx: number, action: string) {
  if (!feedbackInput.value.trim()) return
  const msg = messages.value[msgIdx]
  feedbackLoading.value = true

  const payload: Record<string, unknown> = {
    feedback_type: action,
    content: feedbackInput.value.trim(),
  }
  if (msg.citations && msg.citations.length > 0) {
    payload.node_id = msg.citations[0].chunk_id
  }

  post('/feedback', payload).then(() => {
    feedbackSuccess.value = msgIdx
    feedbackInput.value = ''
    feedbackInputPrompt.value = ''
    activeFeedbackMsgIdx.value = null
    setTimeout(() => {
      if (feedbackSuccess.value === msgIdx) feedbackSuccess.value = null
    }, 2000)
  }).catch(() => {
    feedbackSuccess.value = msgIdx
    feedbackInput.value = ''
    feedbackInputPrompt.value = ''
    activeFeedbackMsgIdx.value = null
    setTimeout(() => {
      if (feedbackSuccess.value === msgIdx) feedbackSuccess.value = null
    }, 2000)
  }).finally(() => {
    feedbackLoading.value = false
  })
}

function handleFeedbackOption(msgIdx: number, option: FeedbackOption) {
  if (option.input) {
    const prompt = option.action === 'update_node' ? '请输入正确的描述：' : '请输入关系信息：'
    promptForInput(msgIdx, option.action, prompt)
  } else {
    submitFeedback(msgIdx, option.action)
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <div class="chat-view">
    <!-- 头部 -->
    <div class="chat-header">
      <div>
        <h2 class="chat-title">💬 多轮对话</h2>
        <p class="chat-desc">基于知识图谱的多轮追问对话</p>
      </div>
      <button class="new-chat-btn" @click="newChat">
        🔄 新对话
      </button>
    </div>

    <!-- 对话区域 -->
    <div ref="chatContainer" class="chat-messages">
      <!-- 空状态 -->
      <div v-if="messages.length === 0 && !loading" class="chat-empty">
        <div class="empty-icon">💬</div>
        <div class="empty-text">开始对话吧</div>
        <div class="empty-hint">可以追问任何教材相关问题</div>
      </div>

      <!-- 消息列表 -->
      <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
        <!-- 头像 -->
        <div class="msg-avatar">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>

        <div class="msg-content">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="msg-bubble user-bubble">
            {{ msg.content }}
          </div>

          <!-- AI 消息 -->
          <div v-else class="msg-bubble ai-bubble">
            <div class="ai-text markdown-body" v-html="renderMarkdown(msg.content)" />

            <!-- 引用来源 -->
            <div v-if="msg.citations && msg.citations.length > 0" class="ai-citations">
              <div class="ai-citations-title">📚 引用来源</div>
              <div v-for="cite in msg.citations" :key="cite.chunk_id" class="ai-citation-item">
                <div class="ai-citation-source">
                  <span>{{ cite.source }}</span>
                  <span>第 {{ cite.page }} 页 · {{ formatScore(cite.score) }}</span>
                </div>
                <p class="ai-citation-text">{{ cite.text }}</p>
              </div>
            </div>

            <!-- Token 统计 -->
            <div v-if="msg.tokenUsage" class="ai-tokens">
              💬 {{ msg.tokenUsage.total.toLocaleString() }} tokens
            </div>

            <!-- 反馈区域 -->
            <div class="ai-feedback">
              <div class="feedback-actions">
                <button class="fb-btn" :class="{ active: activeFeedbackMsgIdx === idx }" @click.stop="toggleFeedbackPanel(idx)" title="有用">
                  👍
                </button>
                <button class="fb-btn" :class="{ active: activeFeedbackMsgIdx === idx }" @click.stop="toggleFeedbackPanel(idx)" title="没用">
                  👎
                </button>
                <transition name="fade">
                  <span v-if="feedbackSuccess === idx" class="fb-success">✓ 已记录</span>
                </transition>
              </div>

              <!-- 反馈面板 -->
              <div v-if="activeFeedbackMsgIdx === idx" class="fb-panel" @click.stop>
                <template v-if="feedbackInputPrompt">
                  <div class="fb-input-row">
                    <input
                      ref="feedbackInputRef"
                      v-model="feedbackInput"
                      class="fb-input"
                      :placeholder="feedbackInputPrompt"
                      @keydown.enter="submitWithInput(idx, 'update_node')"
                      @keydown.escape="cancelInput"
                    />
                    <button class="fb-submit" :disabled="!feedbackInput.trim() || feedbackLoading" @click="submitWithInput(idx, 'update_node')">提交</button>
                    <button class="fb-cancel" @click="cancelInput">取消</button>
                  </div>
                </template>
                <template v-else>
                  <div class="fb-options">
                    <div class="fb-group">
                      <div class="fb-group-label">👍 有用</div>
                      <button v-for="opt in positiveOptions" :key="opt.action" class="fb-option" @click="handleFeedbackOption(idx, opt)">
                        {{ opt.label }}
                      </button>
                    </div>
                    <div class="fb-group">
                      <div class="fb-group-label">👎 需改进</div>
                      <button v-for="opt in negativeOptions" :key="opt.action" class="fb-option" @click="handleFeedbackOption(idx, opt)">
                        {{ opt.label }}
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载动画 -->
      <div v-if="loading" class="msg-row assistant">
        <div class="msg-avatar">🤖</div>
        <div class="msg-content">
          <div class="msg-bubble ai-bubble">
            <div class="typing-dots"><span /><span /><span /></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input-area">
      <div class="chat-input-card">
        <textarea
          v-model="inputText"
          class="chat-textarea"
          placeholder="输入问题... Enter 发送，Shift+Enter 换行"
          rows="2"
          @keydown="handleKeydown"
        />
        <button class="chat-send-btn" :disabled="!inputText.trim() || loading" @click="handleSend">
          <span class="send-arrow">➤</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}

/* 头部 */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.chat-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.chat-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.new-chat-btn {
  font-size: 12px;
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.new-chat-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* 对话区域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 消息行 */
.msg-row {
  display: flex;
  gap: 10px;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  background: #f1f5f9;
}

.msg-content {
  max-width: 75%;
  min-width: 0;
}

/* 消息气泡 */
.msg-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
}

.user-bubble {
  background: var(--color-primary);
  color: white;
  border-bottom-right-radius: 4px;
}

.ai-bubble {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
}

.ai-text {
  color: var(--color-text);
}

.ai-text :deep(p) { margin-bottom: 8px; }
.ai-text :deep(ul), .ai-text :deep(ol) { padding-left: 20px; margin-bottom: 8px; }
.ai-text :deep(li) { margin-bottom: 4px; }
.ai-text :deep(strong) { font-weight: 600; }

/* 引用来源 */
.ai-citations {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
}

.ai-citations-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.ai-citation-item {
  background: #f8fafc;
  border-left: 3px solid var(--color-primary);
  border-radius: 0 6px 6px 0;
  padding: 8px 10px;
  margin-bottom: 6px;
}

.ai-citation-source {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--color-primary);
  font-weight: 600;
  margin-bottom: 4px;
}

.ai-citation-source span:last-child {
  color: var(--color-text-secondary);
  font-weight: normal;
}

.ai-citation-text {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* Token 统计 */
.ai-tokens {
  font-size: 11px;
  color: var(--color-text-secondary);
  text-align: right;
  margin-top: 8px;
}

/* 反馈区域 */
.ai-feedback {
  position: relative;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}

.feedback-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.fb-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: white;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.fb-btn:hover, .fb-btn.active {
  border-color: var(--color-primary);
  background: #eff6ff;
}

.fb-success {
  font-size: 11px;
  color: #16a34a;
}

/* 反馈面板 */
.fb-panel {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  z-index: 10;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  padding: 10px 12px;
  min-width: 200px;
}

.fb-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fb-group-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.fb-option {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: #f8fafc;
  font-size: 12px;
  color: var(--color-text);
  cursor: pointer;
  transition: all 0.15s;
}

.fb-option:hover {
  background: #eff6ff;
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.fb-input-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.fb-input {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 12px;
  outline: none;
}

.fb-input:focus {
  border-color: var(--color-primary);
}

.fb-submit {
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary);
  color: white;
  font-size: 12px;
  cursor: pointer;
}

.fb-submit:disabled {
  opacity: 0.5;
}

.fb-cancel {
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: white;
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
}

/* 输入区域 */
.chat-input-area {
  padding-top: 12px;
  flex-shrink: 0;
}

.chat-input-card {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 10px 12px;
}

.chat-textarea {
  flex: 1;
  padding: 4px 0;
  border: none;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  font-family: inherit;
  background: transparent;
}

.chat-textarea::placeholder {
  color: var(--color-text-secondary);
  opacity: 0.6;
}

.chat-send-btn {
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
  flex-shrink: 0;
  transition: all 0.15s;
}

.chat-send-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: scale(1.05);
}

.chat-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-arrow {
  line-height: 1;
}

/* 打字动画 */
.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: #94a3b8;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* 空状态 */
.chat-empty {
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

/* 动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
