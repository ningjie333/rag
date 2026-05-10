<script setup lang="ts">
import { ref, computed } from 'vue'
import TopBar from '@/components/TopBar.vue'
import GraphView from '@/views/graph/Graph.vue'
import QAView from '@/views/qa/QA.vue'
import ChatView from '@/views/chat/Chat.vue'
import ReportView from '@/views/report/Report.vue'

type RightTab = 'qa' | 'chat' | 'report'
const activeTab = ref<RightTab>('report')

const tabs: { key: RightTab; label: string; icon: string }[] = [
  { key: 'qa', label: '问答', icon: '💡' },
  { key: 'chat', label: '对话', icon: '💬' },
  { key: 'report', label: '报告', icon: '📄' },
]

interface MockBook {
  id: string
  title: string
  chunkCount: number
  selected: boolean
}

const books = ref<MockBook[]>([
  { id: '1', title: '01_局部解剖学', chunkCount: 620, selected: true },
  { id: '2', title: '02_组织学与胚胎学', chunkCount: 122, selected: true },
  { id: '3', title: '03_生理学', chunkCount: 170, selected: true },
  { id: '4', title: '04_医学微生物学', chunkCount: 1202, selected: true },
  { id: '5', title: '05_病理学', chunkCount: 188, selected: true },
  { id: '6', title: '06_传染病学', chunkCount: 1119, selected: true },
  { id: '7', title: '07_病理生理学', chunkCount: 97, selected: true },
])

const nodeCount = ref(127)
const edgeCount = ref(89)
</script>

<template>
  <div class="app-layout">
    <TopBar />

    <div class="main-body">
      <!-- 左侧栏：教材管理 240px -->
      <aside class="left-panel">
        <div class="panel-header">
          <span class="panel-title">教材管理</span>
        </div>

        <button class="btn btn-primary upload-btn">
          📤 上传教材
        </button>

        <div class="book-list">
          <div class="list-label">已导入教材</div>
          <div v-for="book in books" :key="book.id" class="book-item">
            <label class="book-checkbox">
              <input type="checkbox" v-model="book.selected" />
              <span class="checkmark"></span>
              <div class="book-info">
                <div class="book-title">{{ book.title }}</div>
                <div class="book-meta">{{ book.chunkCount }} 个分块</div>
              </div>
            </label>
          </div>
        </div>

        <div class="graph-statistics">
          <div class="stat-label">知识图谱统计</div>
          <div class="stat-row">
            <span class="stat-name">节点数</span>
            <span class="stat-value">{{ nodeCount }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-name">边数</span>
            <span class="stat-value">{{ edgeCount }}</span>
          </div>
        </div>
      </aside>

      <!-- 中间区域：图谱 自适应 -->
      <section class="center-panel">
        <GraphView />
      </section>

      <!-- 右侧 Tab 面板 320px -->
      <aside class="right-panel">
        <div class="tab-header">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            <span class="tab-icon">{{ tab.icon }}</span>
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </div>

        <div class="tab-content">
          <QAView v-if="activeTab === 'qa'" />
          <ChatView v-else-if="activeTab === 'chat'" />
          <ReportView v-else-if="activeTab === 'report'" />
        </div>
      </aside>
    </div>
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --left-panel-width: 240px;
  --right-panel-width: 320px;
  --topbar-height: 48px;
  --color-primary: #2563eb;
  --color-primary-dark: #1d4ed8;
  --color-primary-light: #eff6ff;
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #1e293b;
  --color-text-secondary: #64748b;
  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-danger: #dc2626;
  --color-info: #0891b2;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-lg: 0 4px 12px rgba(0,0,0,0.15);
  --transition: 0.15s ease;
}

body {
  font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.main-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ===== 左侧栏 ===== */
.left-panel {
  width: var(--left-panel-width);
  flex-shrink: 0;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
}

.upload-btn {
  margin: 12px 12px 8px;
  width: calc(100% - 24px);
  justify-content: center;
}

.book-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.list-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 4px 4px;
}

.book-item {
  margin-bottom: 4px;
}

.book-checkbox {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 6px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--transition);
}

.book-checkbox:hover {
  background: var(--color-bg);
}

.book-checkbox input[type="checkbox"] {
  margin-top: 3px;
  accent-color: var(--color-primary);
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.book-info {
  flex: 1;
  min-width: 0;
}

.book-title {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.book-meta {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.graph-statistics {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.stat-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 4px 0;
}

.stat-name {
  color: var(--color-text-secondary);
}

.stat-value {
  font-weight: 600;
  color: var(--color-primary);
}

/* ===== 中间区域 ===== */
.center-panel {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ===== 右侧 Tab 面板 ===== */
.right-panel {
  width: var(--right-panel-width);
  flex-shrink: 0;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-header {
  display: flex;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 8px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition);
  margin-bottom: -1px;
}

.tab-btn:hover {
  color: var(--color-text);
  background: var(--color-bg);
}

.tab-btn.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-icon {
  font-size: 14px;
}

.tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ===== 通用按钮 ===== */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--transition);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-dark);
}

.btn-outline {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-text);
}

.btn-outline:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

/* ===== 滚动条美化 ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* ===== 动画 ===== */
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.fade-in { animation: fadeIn 0.3s ease; }
@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 1s linear infinite; }
</style>
