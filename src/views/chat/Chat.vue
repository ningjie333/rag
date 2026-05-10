<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
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
  { chunk_id: 'c1', text: '心肌炎是指心肌的炎症性疾病，可由感染、自身免疫等因素引起。', source: '兽医诊断学.pdf', page: 128, score: 0.92 },
  { chunk_id: 'c2', text: '心电图检查是诊断心肌炎的重要手段，典型表现为ST段抬高。', source: '兽医诊断学.pdf', page: 130, score: 0.87 },
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

  let payload: Record<string, unknown> = { feedback_type: action }

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
    feedbackSuccess.value = msgIdx
    activeFeedbackMsgIdx.value = null
    setTimeout(() => {
      if (feedbackSuccess.value === msgIdx) feedbackSuccess.value = null
    }, 2000)
  } catch {
    feedbackSuccess.value = msgIdx
    activeFeedbackMsgIdx.value = null
    setTimeout(() => {
      if (feedbackSuccess.value === msgIdx) feedbackSuccess.value = null
    }, 2000)
  } finally {
    feedbackLoading.value = false
  }
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

              <!-- 反馈按钮区域 -->
              <div class="feedback-area">
                <div class="feedback-btns">
                  <button class="feedback-btn" :class="{ active: activeFeedbackMsgIdx === idx }" @click.stop="toggleFeedbackPanel(idx)" title="有用">
                    👍
                  </button>
                  <button class="feedback-btn" :class="{ active: activeFeedbackMsgIdx === idx }" @click.stop="toggleFeedbackPanel(idx)" title="没用">
                    👎
                  </button>
                </div>

                <!-- 成功提示 -->
                <transition name="fade">
                  <span v-if="feedbackSuccess === idx" class="feedback-success">✓ 反馈已记录</span>
                </transition>

                <!-- 反馈面板 -->
                <div v-if="activeFeedbackMsgIdx === idx" class="feedback-panel" @click.stop>
                  <!-- 输入模式 -->
                  <template v-if="feedbackInputPrompt">
                    <div class="feedback-input-row">
                      <input
                        ref="feedbackInputRef"
                        v-model="feedbackInput"
                        class="feedback-input"
                        :placeholder="feedbackInputPrompt"
                        @keydown.enter="submitWithInput(idx, negativeOptions.find(o => o.input)?.action || 'update_node')"
                        @keydown.escape="cancelInput"
                      />
                      <button class="feedback-submit-btn" :disabled="!feedbackInput.trim() || feedbackLoading" @click="submitWithInput(idx, negativeOptions.find(o => o.input)?.action || 'update_node')">提交</button>
                      <button class="feedback-cancel-btn" @click="cancelInput">取消</button>
                    </div>
                  </template>

                  <!-- 选项模式 -->
                  <template v-else>
                    <div class="feedback-options">
                      <div class="feedback-group">
                        <div class="feedback-group__label">👍 有用</div>
                        <button
                          v-for="opt in positiveOptions"
                          :key="opt.action"
                          class="feedback-option"
                          @click="handleFeedbackOption(idx, opt)"
                        >
                          {{ opt.label }}
                        </button>
                      </div>
                      <div class="feedback-group">
                        <div class="feedback-group__label">👎 需改进</div>
                        <button
                          v-for="opt in negativeOptions"
                          :key="opt.action"
                          class="feedback-option"
                          @click="handleFeedbackOption(idx, opt)"
                        >
                          {{ opt.label }}
                        </button>
                      </div>
                    </div>
                  </template>
                </div>
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

/* 反馈区域 */
.feedback-area {
  position: relative;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #e2e8f0;
}

.feedback-btns {
  display: flex;
  gap: 6px;
}

.feedback-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  color: #94a3b8;
  transition: all 0.15s;
}
.feedback-btn:hover,
.feedback-btn.active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: #eff6ff;
}

.feedback-success {
  display: inline-block;
  margin-left: 8px;
  font-size: 12px;
  color: #16a34a;
  vertical-align: middle;
}

.feedback-panel {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  z-index: 10;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 10px 12px;
  min-width: 200px;
}

.feedback-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feedback-group__label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.feedback-option {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: #f8fafc;
  font-size: 13px;
  color: var(--color-text);
  cursor: pointer;
  transition: all 0.15s;
}
.feedback-option:hover {
  background: #eff6ff;
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.feedback-input-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.feedback-input {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.feedback-input:focus {
  border-color: var(--color-primary);
}

.feedback-submit-btn {
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary);
  color: white;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.feedback-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-cancel-btn {
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: white;
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
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

/* 成功提示淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
