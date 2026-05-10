<script setup lang="ts">
import Sidebar from '@/components/Sidebar.vue'
import TopBar from '@/components/TopBar.vue'
</script>

<template>
  <div class="app-layout">
    <Sidebar />
    <div class="main-content">
      <TopBar />
      <main class="page-container">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --sidebar-width: 220px;
  --topbar-height: 48px;
  --color-primary: #2563eb;
  --color-primary-dark: #1d4ed8;
  --color-primary-light: #eff6ff;
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #1e293b;
  --color-text-secondary: #64748b;
  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-danger: #dc2626;
  --color-info: #0891b2;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-lg: 0 4px 12px rgba(0,0,0,0.15);
  --transition: 0.15s ease;
}

body {
  font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
}

.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* 通用页面 */
.page { max-width: 1200px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
.page-subtitle { color: var(--color-text-secondary); margin-bottom: 24px; }

/* 通用卡片 */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 20px;
  transition: all var(--transition);
}
.card:hover { box-shadow: var(--shadow); }

/* 通用按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--transition);
}
.btn-primary { background: var(--color-primary); color: white; }
.btn-primary:hover { background: var(--color-primary-dark); }
.btn-outline { background: transparent; border-color: var(--color-border); color: var(--color-text); }
.btn-outline:hover { border-color: var(--color-primary); color: var(--color-primary); }
.btn-danger { background: var(--color-danger); color: white; }
.btn-sm { padding: 4px 10px; font-size: 12px; }

/* 通用输入 */
.input {
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 14px;
  outline: none;
  transition: border-color var(--transition);
}
.input:focus { border-color: var(--color-primary); }

/* 通用标签 */
.tag {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

/* 通用加载/空状态 */
.loading { display: flex; align-items: center; justify-content: center; padding: 60px; color: var(--color-text-secondary); font-size: 15px; }
.empty-state { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.empty-state .empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state .empty-text { font-size: 15px; margin-bottom: 16px; }

/* 滚动条美化 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* 简单动画 */
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.fade-in { animation: fadeIn 0.3s ease; }
@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 1s linear infinite; }
</style>
