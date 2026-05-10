<script setup lang="ts">
/**
 * 状态徽章
 *
 * 用法：
 *   <StatusBadge status="normal" label="正常" />
 *   <StatusBadge status="warning" label="注意" />
 *   <StatusBadge status="danger" label="异常" />
 */
defineProps<{
  status: 'normal' | 'warning' | 'danger' | 'info'
  label: string
}>()
</script>

<template>
  <span class="status-badge" :class="status">
    <span class="badge-dot" />
    {{ label }}
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
}
.badge-dot { width: 6px; height: 6px; border-radius: 50%; }

.status-badge.normal { background: #f0fdf4; color: #166534; }
.status-badge.normal .badge-dot { background: #16a34a; }

.status-badge.warning { background: #fffbeb; color: #92400e; }
.status-badge.warning .badge-dot { background: #d97706; }

.status-badge.danger { background: #fef2f2; color: #991b1b; }
.status-badge.danger .badge-dot { background: #dc2626; }

.status-badge.info { background: #ecfeff; color: #155e75; }
.status-badge.info .badge-dot { background: #0891b2; }
</style>
