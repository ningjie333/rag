<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()

// 👇 比赛时修改
const projectName = '🌳 温柔树洞' // 改项目名
const menuItems = [
  { path: '/', label: '首页', icon: '🏠' },
  { path: '/chat', label: '开始倾诉', icon: '💬' },
  { path: '/dashboard', label: '心理画像', icon: '📊' },
]
</script>

<template>
  <aside class="sidebar">
    <div class="logo">
      <span class="logo-icon">🏥</span>
      <span class="logo-text">{{ projectName }}</span>
    </div>
    <nav class="menu">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="menu-item"
        :class="{ active: route.path === item.path }"
      >
        <span class="menu-icon">{{ item.icon }}</span>
        <span class="menu-label">{{ item.label }}</span>
      </router-link>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.logo {
  padding: 20px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--color-border);
}

.logo-icon { font-size: 24px; }
.logo-text { font-size: 16px; font-weight: 700; color: var(--color-primary); }

.menu {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius);
  text-decoration: none;
  color: var(--color-text-secondary);
  font-size: 13px;
  transition: all var(--transition);
  flex-shrink: 0;
}

.menu-item:hover { background: var(--color-bg); color: var(--color-text); }
.menu-item.active { background: var(--color-primary-light); color: var(--color-primary); font-weight: 500; }
.menu-icon { font-size: 16px; }
</style>
