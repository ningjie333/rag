<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { ref, onMounted } from 'vue'
import { get } from '@/api/client'

const loading = ref(true)
const items = ref<any[]>([])

onMounted(async () => {
  try {
    // 👇 比赛时改为实际接口
    // items.value = await get<any[]>('/items')
  } catch (e) { /* 静默处理 */ }
  loading.value = false
})
</script>

<template>
  <div class="dashboard page fade-in">
    <PageHeader title="数据面板" subtitle="查看和管理所有数据">
      <template #actions>
        <button class="btn btn-primary">+ 新建</button>
      </template>
    </PageHeader>

    <LoadingSpinner v-if="loading" />
    <EmptyState v-else-if="!items.length" icon="📭" text="暂无数据" actionLabel="创建第一条" />

    <div v-else class="data-list">
      <div v-for="item in items" :key="item.id" class="data-card card">
        {{ item.name || item.title }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.data-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.data-card { padding: 16px; }
</style>
