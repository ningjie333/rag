<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  icon?: string
  color?: string
}>()
</script>

<template>
  <div class="stat-card card fade-in">
    <div class="stat-icon" :style="{ background: color || 'var(--color-primary-light)' }">
      {{ icon || '📊' }}
    </div>
    <div class="stat-info">
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
  </div>
</template>

<style scoped>
.stat-card { display: flex; align-items: center; gap: 16px; padding: 20px; }
.stat-icon { width: 48px; height: 48px; border-radius: var(--radius); display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--color-primary); }
.stat-label { font-size: 13px; color: var(--color-text-secondary); margin-top: 2px; }
</style>
