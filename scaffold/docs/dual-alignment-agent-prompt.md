# 双重对齐 + 可视化对比 Agent 任务提示词

## 任务目标

实现"跨教材双重语义对齐 + 压缩效果可视化对比"功能。

## 需求描述

跨教材整合时，不仅做节点去重，还要做"表述对齐"（同义概念识别），并输出可视化的压缩对比。

## 技术方案

### 双重对齐（Dual Alignment）

在 `relation_inferrer.py` 中新增 `dual_align_concepts()` 函数：

```
第一重对齐：表面匹配
  - 完全相同名称 → 直接合并
  - 别名/同义词表匹配 → 合并

第二重对齐：语义匹配
  - 用 LLM 判断"这两个概念是否同一事物"
  - embedding 余弦相似度 > 0.85 → 候选 → LLM 最终判断
```

### API 扩展

扩展 `POST /api/graph/merge` 响应，增加：

```json
{
  "success": true,
  "dual_alignment": {
    "surface_matches": 15,
    "semantic_matches": 23,
    "total_aligned": 38
  },
  "compression_detail": {
    "before": 150,
    "after_dedup": 120,
    "after_alignment": 42,
    "surface_ratio": 0.80,
    "semantic_ratio": 0.28
  }
}
```

### 可视化对比

前端 `Graph.vue` 新增"整合对比"Tab，展示：

1. **压缩前 → 压缩后** 双栏图谱
2. **压缩统计条**：
   - 原始节点数 → 整合后节点数
   - 压缩比数字（醒目显示）
3. **去重示例列表**（可展开）：
   - 概念A（教材1）≡ 概念B（教材2）→ 合并为"统一名称"

### 前端新增视图

在 `src/views/graph/Graph.vue` 中添加：

```vue
<template>
  <div class="comparison-view">
    <div class="stats-bar">
      <div class="stat">
        <span class="label">整合前</span>
        <span class="value">{{ stats.before }}</span>
      </div>
      <div class="arrow">→</div>
      <div class="stat">
        <span class="label">整合后</span>
        <span class="value">{{ stats.after }}</span>
      </div>
      <div class="compression-badge">
        压缩比: {{ (stats.after/stats.before * 100).toFixed(0) }}%
      </div>
    </div>
    <!-- 去重示例列表 -->
    <div class="dedup-examples">
      <div v-for="example in dedupExamples" class="example-card">
        <span class="concept-a">{{ example.conceptA }}</span>
        <span class="merge-icon">≡</span>
        <span class="concept-b">{{ example.conceptB }}</span>
        <span class="merged-as">→ {{ example.mergedAs }}</span>
      </div>
    </div>
  </div>
</template>
```

## 交付物

1. **后端**：`relation_inferrer.py` 新增 `dual_align_concepts()`，扩展 `/graph/merge` 响应
2. **前端**：`Graph.vue` 新增"整合对比"Tab（切换按钮在图谱右上角）
3. **文档**：更新 `docs/api-contract.md` 添加 `merge` 新字段

## 验收标准

1. `POST /api/graph/merge` 返回 `dual_alignment` 和 `compression_detail` 字段
2. 前端图谱 Tab 可切换"图谱视图"和"整合对比"
3. 整合对比显示压缩前后数字 + 去重示例

## 禁止事项

- ❌ 不改现有 API 字段名（向后兼容）
- ❌ 不做 3D 图谱对比（2D 够用）
- ❌ 不写测试

## 开始

1. 先改 `relation_inferrer.py` 添加 `dual_align_concepts()`
2. 改 `routers/kg.py` 的 `/graph/merge` 响应
3. 前端 `Graph.vue` 添加对比 Tab
4. 更新 api-contract.md
5. task-board.md 记录