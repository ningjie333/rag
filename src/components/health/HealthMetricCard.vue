<script setup lang="ts">
/**
 * 健康指标卡片
 *
 * 用法：
 *   <HealthMetricCard
 *     label="血压"
 *     value="120/80"
 *     unit="mmHg"
 *     status="normal"  // normal | warning | danger
 *     :trend="5"       // 正数上升，负数下降
 *   />
 */
defineProps<{
  label: string
  value: string | number
  unit?: string
  status?: 'normal' | 'warning' | 'danger'
  trend?: number
}>()
</script>

<template>
  <div class="metric-card card fade-in" :class="status || 'normal'">
    <div class="metric-header">
      <span class="metric-label">{{ label }}</span>
      <span v-if="trend" class="metric-trend" :class="trend > 0 ? 'up' : 'down'">
        {{ trend > 0 ? '↑' : '↓' }}{{ Math.abs(trend) }}
      </span>
    </div>
    <div class="metric-value">
      {{ value }}
      <span v-if="unit" class="metric-unit">{{ unit }}</span>
    </div>
    <div class="metric-status-bar" :class="status || 'normal'" />
  </div>
</template>

<style scoped>
.metric-card { padding: 16px; position: relative; overflow: hidden; }
.metric-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.metric-label { font-size: 13px; color: var(--color-text-secondary); }
.metric-trend { font-size: 12px; font-weight: 600; }
.metric-trend.up { color: var(--color-danger); }
.metric-trend.down { color: var(--color-success); }
.metric-value { font-size: 28px; font-weight: 700; }
.metric-unit { font-size: 14px; font-weight: 400; color: var(--color-text-secondary); margin-left: 4px; }
.metric-status-bar { position: absolute; bottom: 0; left: 0; right: 0; height: 3px; }
.metric-status-bar.normal { background: var(--color-health-good); }
.metric-status-bar.warning { background: var(--color-health-warning); }
.metric-status-bar.danger { background: var(--color-health-danger); }

/* 边框颜色 */
.metric-card.normal { border-left: 3px solid var(--color-health-good); }
.metric-card.warning { border-left: 3px solid var(--color-health-warning); }
.metric-card.danger { border-left: 3px solid var(--color-health-danger); }
</style>
