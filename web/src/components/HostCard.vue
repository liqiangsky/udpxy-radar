<template>
  <div v-if="item" class="iptv-grid-card">

    <div class="section-host">
      <div class="host-ip font-mono">{{ item.host }}</div>
      <button class="copy-btn" @click.stop="$emit('copy', item.host)">
        <span class="material-symbols-outlined icon-g">content_copy</span>
      </button>
    </div>

    <div class="section-metrics-grid">
      <div class="grid-item">
        <span class="badge-lbl">地区</span>
        <span class="badge-txt color-blue">{{ item.region }}</span>
      </div>

      <div class="grid-item">
        <span class="badge-lbl">运营商</span>
        <span class="badge-txt color-blue">{{ item.operator }}</span>
      </div>

      <div class="grid-item">
        <span class="badge-lbl">延迟</span>
        <div class="delay-interactive-badge" :class="{ 'state-error': item.delay < 0 }" @click.stop="$emit('test', item)">
          <span class="material-symbols-outlined icon-g">bolt</span>
          <span class="badge-txt font-mono">{{ item.delay }} ms</span>
        </div>
      </div>

      <div class="grid-item">
        <span class="badge-lbl">来源</span>
        <span class="source-badge">
          <img :src="getItemSourceImg(item.sourceType)" class="source-logo" />
          <span class="badge-txt">{{ item.sourceName }}</span>
        </span>
      </div>

      <div class="grid-item time-column full-width">
        <span class="badge-lbl">发现</span>
        <div class="time-wrapper">
          <span class="material-symbols-outlined icon-g">history</span>
          <span class="badge-txt color-gray font-mono">{{ item.createTime }}</span>
        </div>
      </div>

      <div class="grid-item time-column full-width">
        <span class="badge-lbl">验证</span>
        <div class="time-wrapper">
          <span class="material-symbols-outlined icon-g">update</span>
          <span class="badge-txt color-gray font-mono">{{ item.lastSeen }}</span>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import sourceLogoGithub from '@/assets/github.png'
import sourceLogo0zone from '@/assets/zero_zone.png'
import sourceLogoZoomEye from '@/assets/zoomeye.png'
import sourceLogoDayDayMap from '@/assets/daydaymap.svg'

defineProps({
  item: {
    type: Object,
    default: null
  }
})
defineEmits(['copy', 'test'])

const getItemSourceImg = (sourceType) => {
  return {
    'ozone': sourceLogo0zone,
    'github': sourceLogoGithub,
    'zoomeye': sourceLogoZoomEye,
    'daydaymap': sourceLogoDayDayMap,
  }[sourceType]
}
</script>

<style scoped>
.iptv-grid-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 18px;
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.01);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-host {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.host-ip {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.font-mono {
  font-family: var(--font-mono);
  letter-spacing: -0.3px;
}

.copy-btn {
  background: var(--bg-neutral);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border: none;
  cursor: pointer;
}
.copy-btn:active { transform: scale(0.9); background: #E8E8ED; }

.section-metrics-grid {
  border-top: 1px solid #F1F5F9;
  padding-top: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

.grid-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.grid-item.full-width {
  grid-column: span 2;
}

.badge-lbl {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  width: 38px;
}

.badge-txt {
  font-size: 13px;
  font-weight: 600;
}

.color-blue { color: var(--color-blue); }
.color-gray { color: var(--text-secondary); }
.color-dark { color: var(--text-primary); }

.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--bg-neutral);
  font-size: 12px;
}
.source-logo {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

.delay-interactive-badge {
  background: var(--bg-status-good);
  color: var(--color-green);
  padding: 4px 8px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.delay-interactive-badge:active { transform: scale(0.95); }

.time-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-g {
  font-size: 16px !important;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  display: inline-block;
  vertical-align: middle;
}
.copy-btn .icon-g { color: var(--text-muted); }
.delay-interactive-badge .icon-g { color: var(--color-green); }
.delay-interactive-badge.state-error {
  background: #fdecea;
  color: #e5484d;
}
.delay-interactive-badge.state-error .icon-g { color: #e5484d; }
.time-wrapper .icon-g { color: var(--text-muted); }
</style>
