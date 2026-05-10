<script setup lang="ts">
import { ref } from 'vue'
import { get } from '@/api/client'

const searchQuery = ref('')
const searchResults = ref<any[]>([])
const showResults = ref(false)

async function onSearch() {
  if (!searchQuery.value.trim()) return
  try {
    // 👇 比赛时改为实际搜索接口
    searchResults.value = await get<any[]>(`/search?q=${encodeURIComponent(searchQuery.value)}`)
    showResults.value = true
  } catch (e) {
    // 搜索失败静默处理
  }
}

function onClickOutside() {
  showResults.value = false
}
</script>

<template>
  <header class="topbar">
    <div class="search-box" @click.stop>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索..."
        class="input"
        @keyup.enter="onSearch"
        @focus="showResults = searchResults.length > 0"
      />
      <button class="btn btn-primary btn-sm" @click="onSearch">🔍</button>
      <div v-if="showResults && searchResults.length" class="search-dropdown" @click="onClickOutside">
        <div v-for="r in searchResults" :key="r.id" class="search-result-item">
          <span class="result-title">{{ r.title || r.name }}</span>
        </div>
      </div>
    </div>
    <div class="topbar-actions">
      <span class="version">v0.1.0</span>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  height: var(--topbar-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 16px;
  flex-shrink: 0;
}

.search-box {
  flex: 1;
  max-width: 480px;
  position: relative;
  display: flex;
}

.search-box input {
  border-radius: var(--radius) 0 0 var(--radius);
  border-right: none;
}

.search-box .btn {
  border-radius: 0 var(--radius) var(--radius) 0;
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  max-height: 400px;
  overflow-y: auto;
}

.search-result-item {
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
  cursor: pointer;
}

.search-result-item:hover { background: var(--color-bg); }

.version { font-size: 12px; color: var(--color-text-secondary); }
</style>
