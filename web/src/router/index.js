import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 默认重定向到移动端主页
  {
    path: '/',
    redirect: '/hosts'
  },
  // 移动端路由组
  {
    path: '/hosts',
    component: () => import('@/routes/HostList.vue') // 移动端主页
  },
  {
    path: '/config',
    component: () => import('@/routes/ScanConfig.vue') // 扫描配置页
  },
  {
    path: '/templates',
    component: () => import('@/routes/ConfigTemplates.vue') // 配置模板页
  },
  {
    path: '/settings',
    component: () => import('@/routes/GlobalSettings.vue') // 全局设置页
  },
  {
    path: '/logs',
    component: () => import('@/routes/ServerLogs.vue'), // 后台日志页
    meta: { hideNavbar: true }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
