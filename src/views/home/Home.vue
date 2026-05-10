<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get } from '@/api/client'
import StatCard from '@/components/StatCard.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

// 👇 比赛时改为实际数据
const stats = ref([
  { label: '总数据量', value: 0, icon: '📦', color: '#eff6ff' },
  { label: '今日新增', value: 0, icon: '📈', color: '#f0fdf4' },
  { label: '活跃用户', value: 0, icon: '👥', color: '#fef3c7' },
  { label: '系统状态', value: '正常', icon: '✅', color: '#ecfdf5' },
])
const loading = ref(true)
const projectName = '{{PROJECT_NAME}}' // 👇 比赛时改项目名

onMounted(async () => {
  try {
    // 👇 比赛时改为实际接口
    // const data = await get<any>('/stats')
    // stats.value[0].value = data.total
    // ...
  } catch (e) { /* 静默处理 */ }
  loading.value = false
})
</script>

<template>
  <div class="home page fade-in">
    <h1 class="page-title">{{ projectName }}</h1>
    <p class="page-subtitle">生命健康数据管理平台</p>

    <LoadingSpinner v-if="loading" text="加载中..." />

    <template v-else>
      <div class="stats-grid">
        <StatCard
          v-for="s in stats"
          :key="s.label"
          :label="s.label"
          :value="s.value"
          :icon="s.icon"
          :color="s.color"
        />
      </div>

      <section class="section">
        <h2>快速入口</h2>
        <div class="quick-links">
          <router-link to="/dashboard" class="quick-link card">
            <span class="ql-icon">📊</span>
            <span class="ql-label">数据面板</span>
          </router-link>
          <!-- 👇 比赛时添加更多入口 -->
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
.section { margin-bottom: 32px; }
.section h2 { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.quick-links { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.quick-link { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 24px; text-decoration: none; color: var(--color-text); cursor: pointer; }
.quick-link:hover { border-color: var(--color-primary); }
.ql-icon { font-size: 32px; }
.ql-label { font-size: 14px; font-weight: 500; }
</style>
