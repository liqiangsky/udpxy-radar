<template>
  <router-view />

  <nav class="bottom-tabbar" v-if="showTabbar">
    <router-link to="/hosts" class="tab-item" active-class="active" exact-active-class="active">
      <span class="material-symbols-outlined tab-icon-g">tv</span>
      <span class="tab-text">组播源</span>
    </router-link>

    <router-link to="/templates" class="tab-item" active-class="active">
      <span class="material-symbols-outlined tab-icon-g">widgets</span>
      <span class="tab-text">配置模板</span>
    </router-link>

    <router-link to="/config" class="tab-item" active-class="active">
      <span class="material-symbols-outlined tab-icon-g">analytics</span>
      <span class="tab-text">扫描配置</span>
    </router-link>

    <router-link to="/settings" class="tab-item" active-class="active">
      <span class="material-symbols-outlined tab-icon-g">settings</span>
      <span class="tab-text">全局设置</span>
    </router-link>

    <button class="tab-item logout-btn" @click="handleLogout">
      <span class="material-symbols-outlined tab-icon-g">logout</span>
      <span class="tab-text">退出</span>
    </button>
  </nav>

  <!-- 未登录时的登录按钮 -->
  <button v-if="showLoginBtn" class="floating-login" @click="$router.push('/login')">
    <span class="material-symbols-outlined">login</span>
    <span>登录</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()
const router = useRouter()

const showTabbar = computed(() => {
  return authStore.isLoggedIn && !route.meta?.hideNavbar
})

const showLoginBtn = computed(() => {
  return !authStore.isLoggedIn && route.path !== '/login'
})

const handleLogout = async () => {
  await authStore.logout()
  router.push('/')
}
</script>

<style scoped>
.bottom-tabbar {
  position: fixed;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 358px;
  height: 60px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.02);
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 99;
  margin-bottom: env(safe-area-inset-bottom);
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.25s ease;
  width: 30%;
}

.tab-icon-g {
  font-size: 22px !important;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-text {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-sans);
}

.tab-item.active {
  color: var(--color-blue);
}

.tab-item.active .tab-icon-g {
  font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  transform: scale(1.08);
}

.logout-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-red);
  width: 20%;
}

.floating-login {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-blue);
  color: #fff;
  border: none;
  border-radius: 28px;
  padding: 14px 32px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 8px 32px rgba(0, 122, 255, 0.3);
  transition: all 0.2s ease;
  z-index: 99;
}

.floating-login:active {
  transform: translateX(-50%) scale(0.96);
}

.floating-login .material-symbols-outlined {
  font-size: 20px !important;
}
</style>
