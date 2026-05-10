<script setup lang="ts">
defineProps<{ text?: string }>()
</script>

<template>
  <div class="loading fade-in">
    <div class="spinner"></div>
    <span v-if="text" class="loading-text">{{ text }}</span>
  </div>
</template>

<style scoped>
.loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px; gap: 12px; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
.loading-text { color: var(--color-text-secondary); font-size: 14px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
