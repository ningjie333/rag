# PDF 导出 Agent 任务提示词

## 任务目标

为"学科知识整合智能体"的前端添加**报告导出为 PDF** 功能。

## 技术背景

- 前端已有 `marked` 渲染 Markdown 报告（`src/views/report/Report.vue`）
- 已完成 Markdown 预览 + 文本下载
- 需要加 PDF 导出功能

## 交付物

修改 `src/views/report/Report.vue`，添加 PDF 下载按钮。

## 技术方案

### 推荐：html2pdf.js（CDN 或 npm）
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
```

或 npm：
```bash
npm install html2pdf.js
```

### 使用方式
```js
import html2pdf from 'html2pdf.js'

async function exportPDF() {
  const element = document.getElementById('report-content')
  const opt = {
    margin: [10, 10, 10, 10],
    filename: 'knowledge-report.pdf',
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  }
  await html2pdf().set(opt).from(element).save()
}
```

## UI 要求

1. 在"下载 Markdown"按钮旁边加"导出 PDF"按钮
2. 按钮样式与现有下载按钮一致
3. 导出时显示 loading 状态，结束后恢复

## 验收标准

1. 点击"导出 PDF"按钮，浏览器下载 `knowledge-report.pdf`
2. PDF 内容包含报告的完整 Markdown 渲染（标题/列表/表格等）
3. 格式整齐，中文正常显示

## 禁止事项

- ❌ 不引入太大的库（PDF 体积控制在 2MB 以内）
- ❌ 不做服务器端 PDF 生成（纯前端）
- ❌ 不改已有的 Markdown 渲染逻辑

## 开始

修改 `src/views/report/Report.vue`，添加 PDF 导出功能。在 task-board.md 更新 FE-7 状态。