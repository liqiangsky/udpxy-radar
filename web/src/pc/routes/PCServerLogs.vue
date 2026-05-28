<template>
  <div class="pc-page">
    <div class="pc-page-header">
      <h1 class="pc-page-title">后台日志</h1>
      <div style="display: flex; align-items: center; gap: 12px">
        <div class="log-level-chips">
          <span
            v-for="lv in ['ALL', 'INFO', 'WARNING', 'ERROR']"
            :key="lv"
            class="log-level-chip"
            :class="{ active: logLevel === lv }"
            @click="logLevel = lv"
          >{{ lv === 'ALL' ? '全部' : lv }}</span>
        </div>
        <span class="log-count">{{ logs.length }} 条</span>
        <button class="refresh-btn" @click="refreshLogs">
          <span class="material-symbols-outlined" :class="{ spin: refreshing }">refresh</span>
        </button>
      </div>
    </div>

    <div class="log-viewer" ref="logViewerRef">
      <div v-if="logs.length === 0 && !initialized" class="log-empty">
        <span class="material-symbols-outlined log-empty-icon">receipt_long</span>
        <p>正在加载日志...</p>
      </div>
      <div v-else-if="logs.length === 0" class="log-empty">
        <span class="material-symbols-outlined log-empty-icon">inbox</span>
        <p>暂无日志</p>
      </div>
      <div v-else v-for="(line, i) in logs" :key="i" class="log-line" :class="getLogLevelClass(line)">
        <span class="log-time">{{ parseLogLine(line).time }}</span>
        <span class="log-text">{{ parseLogLine(line).content }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import request from '@/api'

const logs = ref([])
const logLevel = ref('ALL')
const refreshing = ref(false)
const initialized = ref(false)
const logViewerRef = ref(null)

let pollTimer = null

const parseLogLine = (line) => {
  const match = line.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(.*)$/)
  if (match) return { time: match[1], content: match[2] }
  return { time: '', content: line }
}

const fetchLogs = async () => {
  try {
    const params = { lines: 500 }
    if (logLevel.value !== 'ALL') params.level = logLevel.value
    const res = await request.get('/logs', { params })
    const newLogs = res.logs || []

    if (!initialized.value) {
      logs.value = newLogs
      initialized.value = true
      setTimeout(() => {
        if (logViewerRef.value) {
          logViewerRef.value.scrollTop = logViewerRef.value.scrollHeight
        }
      }, 100)
    } else {
      const lastLine = logs.value[logs.value.length - 1]
      const lastIdx = newLogs.indexOf(lastLine)
      if (lastIdx >= 0 && lastIdx < newLogs.length - 1) {
        const appended = newLogs.slice(lastIdx + 1)
        logs.value.push(...appended)
        const el = logViewerRef.value
        if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 100) {
          el.scrollTop = el.scrollHeight
        }
      }
    }
  } catch {
    // 静默
  }
}

const refreshLogs = async () => {
  refreshing.value = true
  logs.value = []
  initialized.value = false
  await fetchLogs()
  refreshing.value = false
}

const getLogLevelClass = (line) => {
  const { content } = parseLogLine(line)
  if (content.includes('[ERROR]') || content.includes('[EXCEPTION]') || content.includes('[CRITICAL]')) return 'log-error'
  if (content.includes('[WARNING]')) return 'log-warning'
  return ''
}

watch(logLevel, () => {
  logs.value = []
  initialized.value = false
  fetchLogs()
})

onMounted(() => {
  fetchLogs()
  pollTimer = setInterval(fetchLogs, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
@import '../pc.css';

.log-level-chips {
  display: flex;
  align-items: center;
  gap: 6px;
}

.log-level-chip {
  font-size: 12px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 14px;
  background: var(--bg-neutral);
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  transition: all 0.15s ease;
}

.log-level-chip.active {
  background: rgba(0, 122, 255, 0.12);
  color: var(--color-blue);
}

.log-count {
  font-size: 12px;
  color: var(--text-muted);
}

.refresh-btn {
  background: var(--bg-neutral);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn .material-symbols-outlined {
  font-size: 20px !important;
  color: var(--text-muted);
}

.refresh-btn:active { transform: scale(0.9); }

.log-viewer {
  background: #1e1e1e;
  border-radius: var(--radius-card);
  padding: 16px;
  height: calc(100vh - 160px);
  max-height: calc(100vh - 160px);
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.6;
  color: #d4d4d4;
  word-break: break-all;
}

.log-viewer::-webkit-scrollbar { width: 6px; }
.log-viewer::-webkit-scrollbar-track { background: transparent; }
.log-viewer::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }

.log-line { padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.log-line:last-child { border-bottom: none; }
.log-time {
  display: block;
  font-size: 10px;
  color: #666;
  margin-bottom: 2px;
}
.log-text { white-space: pre-wrap; }
.log-error .log-text { color: #f48771; }
.log-warning .log-text { color: #dcdcaa; }

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #888;
}

.log-empty-icon {
  font-size: 48px !important;
  margin-bottom: 12px;
  color: #555;
}

.log-empty p {
  margin: 0;
  font-size: 14px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.spin { animation: spin 1s linear infinite; }
</style>
