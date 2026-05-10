import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/home/Home.vue')
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/dashboard/Dashboard.vue')
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/chat/Chat.vue')
    },
  ]
})

export default router
