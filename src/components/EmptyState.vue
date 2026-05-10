<script setup lang="ts">
defineProps<{
  icon?: string
  text?: string
  actionLabel?: string
}>()
defineEmits<{ action: [] }>()
</script>

<template>
  <div class="empty-state fade-in">
    <div class="empty-icon">{{ icon || '📭' }}</div>
    <div class="empty-text">{{ text || '暂无数据' }}</div>
    <button v-if="actionLabel" class="btn btn-primary" @click="$emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>

<style scoped>
.empty-state { text-align: center; padding: 60px 20px; color: var(--color-text-secondary); }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-text { font-size: 15px; margin-bottom: 16px; }
</style>
