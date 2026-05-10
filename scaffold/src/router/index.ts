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
      path: '/upload',
      name: 'upload',
      component: () => import('@/views/upload/Upload.vue')
    },
    {
      path: '/graph',
      name: 'graph',
      component: () => import('@/views/graph/Graph.vue')
    },
    {
      path: '/qa',
      name: 'qa',
      component: () => import('@/views/qa/QA.vue')
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/chat/Chat.vue')
    },
    {
      path: '/report',
      name: 'report',
      component: () => import('@/views/report/Report.vue')
    },
  ]
})

export default router
