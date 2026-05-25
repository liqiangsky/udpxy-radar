import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 默认重定向到移动端主页
  {
    path: '/',
    redirect: '/mobile'
  },
  // 移动端路由组
  {
    path: '/mobile',
    component: () => import('../mobile/routes/HostList.vue') // 移动端主页
  },
  {
    path: '/mobile/config',
    component: () => import('../mobile/routes/ScanConfig.vue') // 扫描配置页
  },
  {
    path: '/mobile/templates',
    component: () => import('../mobile/routes/ConfigTemplates.vue') // 配置模板页
  },
  {
    path: '/mobile/settings',
    component: () => import('@/mobile/routes/GlobalSettings.vue') // 👈 核心新增：全局设置页
  }
  // 以后做 web 端时，在这里直接加 /web 路由即可，两套完全独立
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
