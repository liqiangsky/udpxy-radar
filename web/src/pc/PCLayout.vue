<template>
  <div class="pc-layout">
    <aside class="pc-sidebar">
      <div class="sidebar-brand">
        <span class="material-symbols-outlined">radar</span>
        <span>UDProxy Radar</span>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/pc" class="nav-item" exact-active-class="active">
          <span class="material-symbols-outlined">tv</span>
          <span>组播源</span>
        </router-link>
        <router-link to="/pc/templates" class="nav-item" active-class="active">
          <span class="material-symbols-outlined">widgets</span>
          <span>配置模板</span>
        </router-link>
        <router-link to="/pc/config" class="nav-item" active-class="active">
          <span class="material-symbols-outlined">analytics</span>
          <span>扫描配置</span>
        </router-link>
        <router-link to="/pc/settings" class="nav-item" active-class="active">
          <span class="material-symbols-outlined">settings</span>
          <span>全局设置</span>
        </router-link>
        <router-link to="/pc/logs" class="nav-item" active-class="active">
          <span class="material-symbols-outlined">receipt_long</span>
          <span>后台日志</span>
        </router-link>
      </nav>
    </aside>

    <main class="pc-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
@import '../pc/pc.css';
</style>
