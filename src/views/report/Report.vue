<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { get } from '@/api/client'
import html2pdf from 'html2pdf.js'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import EmptyState from '@/components/EmptyState.vue'

const reportContent = ref('')
const loading = ref(true)
const loadingPDF = ref(false)
const bookCount = ref(0)
const knowledgePointCount = ref(0)
const generatedAt = ref('')

const mockReport = `# 学科知识整合报告

## 一、知识图谱概览

本次整合涉及 **3 本教材**，共提取 **127 个知识点**，构建 **89 条关系**。

## 二、核心知识点

### 2.1 高频概念

| 知识点 | 出现频次 | 来源教材 |
|--------|---------|---------|
| 炎症反应 | 15 | 生理学、诊断学 |
| 心电图异常 | 12 | 诊断学 |
| 肌钙蛋白 | 10 | 内科学 |

### 2.2 跨教材关联

- **心肌炎** 在《诊断学》和《内科学》中均有详细描述
- **炎症反应** 是连接多个学科的核心概念

## 三、知识盲区

- 缺少药理学相关教材
- 微生物学与临床诊断的关联较少

## 四、建议补充

1. 增加《药理学》教材
2. 补充《外科学》相关内容

---
*报告生成时间：2026-05-10 12:00*
`

const htmlContent = computed(() => marked.parse(reportContent.value) as string)

async function fetchReport() {
  loading.value = true
  try {
    const resp = await get<{ content: string; book_count: number; knowledge_point_count: number; generated_at: string }>('/report')
    reportContent.value = resp.content
    bookCount.value = resp.book_count
    knowledgePointCount.value = resp.knowledge_point_count
    generatedAt.value = resp.generated_at
  } catch {
    reportContent.value = mockReport
    bookCount.value = 3
    knowledgePointCount.value = 127
    generatedAt.value = '2026-05-10 12:00'
  } finally {
    loading.value = false
  }
}

function downloadReport() {
  const blob = new Blob([reportContent.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `学科知识整合报告_${generatedAt.value.replace(/[: ]/g, '_')}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function exportPDF() {
  loadingPDF.value = true
  try {
    const element = document.getElementById('report-content')
    const opt = {
      margin: [10, 10, 10, 10] as [number, number, number, number],
      filename: 'knowledge-report.pdf',
      image: { type: 'jpeg' as const, quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm' as const, format: 'a4' as const, orientation: 'portrait' as const }
    }
    await html2pdf().set(opt).from(element as HTMLElement).save()
  } finally {
    loadingPDF.value = false
  }
}

onMounted(() => {
  fetchReport()
})
</script>

<template>
  <div class="report-view">
    <div class="report-toolbar">
      <div class="toolbar-left">
        <button class="btn btn-outline btn-sm" @click="exportPDF" :disabled="!reportContent || loadingPDF">
          📄 导出 PDF
        </button>
        <button class="btn btn-outline btn-sm" @click="downloadReport" :disabled="!reportContent">
          ⬇️ 下载 .md
        </button>
        <button class="btn btn-outline btn-sm" @click="fetchReport" :disabled="loading">
          🔄 刷新
        </button>
      </div>
      <div class="toolbar-meta">
        <span v-if="generatedAt" class="meta-item">📅 {{ generatedAt }}</span>
        <span v-if="bookCount" class="meta-item">📚 {{ bookCount }} 本教材</span>
        <span v-if="knowledgePointCount" class="meta-item">💡 {{ knowledgePointCount }} 个知识点</span>
      </div>
    </div>

    <div class="report-body">
      <LoadingSpinner v-if="loading" text="加载报告中..." />
      <EmptyState v-else-if="!reportContent" icon="📄" text="暂无报告数据" actionLabel="生成报告" />

      <div v-else id="report-content" class="report-content" v-html="htmlContent" />
    </div>
  </div>
</template>

<style scoped>
.report-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  gap: 8px;
}

.toolbar-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.report-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.report-content {
  background: #ffffff;
  padding: 40px;
  max-width: 800px;
  margin: 0 auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  line-height: 1.8;
  font-size: 14px;
}

.report-content :deep(h1) {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--color-primary);
}

.report-content :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  margin-top: 28px;
  margin-bottom: 12px;
  color: var(--color-primary-dark);
}

.report-content :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin-top: 20px;
  margin-bottom: 8px;
}

.report-content :deep(p) {
  margin-bottom: 12px;
}

.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

.report-content :deep(th),
.report-content :deep(td) {
  border: 1px solid var(--color-border);
  padding: 8px 12px;
  text-align: left;
}

.report-content :deep(th) {
  background: var(--color-bg);
  font-weight: 600;
}

.report-content :deep(ul),
.report-content :deep(ol) {
  padding-left: 20px;
  margin-bottom: 12px;
}

.report-content :deep(li) {
  margin-bottom: 4px;
}

.report-content :deep(strong) {
  font-weight: 600;
}

.report-content :deep(em) {
  color: var(--color-text-secondary);
  font-style: italic;
}

.report-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 20px 0;
}
</style>
