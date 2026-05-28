<template>
  <router-view />

  <nav class="bottom-tabbar" v-show="!$route.meta?.hideNavbar && !$route.path.startsWith('/pc')">
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
  </nav>
</template>

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
</style>
