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
    component: () => import('@/mobile/routes/GlobalSettings.vue') // 全局设置页
  },
  {
    path: '/mobile/logs',
    component: () => import('@/mobile/routes/ServerLogs.vue'), // 后台日志页
    meta: { hideNavbar: true }
  },
  // PC 路由组（使用独立 Layout 包裹）
  // {
  //   path: '/pc',
  //   component: () => import('../pc/PCLayout.vue'),
  //   children: [
  //     { path: '', component: () => import('../pc/routes/PCHostList.vue') },
  //     { path: 'templates', component: () => import('../pc/routes/PCConfigTemplates.vue') },
  //     { path: 'config', component: () => import('../pc/routes/PCScanConfig.vue') },
  //     { path: 'settings', component: () => import('../pc/routes/PCGlobalSettings.vue') },
  //     { path: 'logs', component: () => import('../pc/routes/PCServerLogs.vue') },
  //   ]
  // }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
