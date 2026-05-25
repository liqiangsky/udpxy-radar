<template>
  <div class="page-container">

    <div class="page-header">
      <h1 class="page-title">扫描配置</h1>
      <button class="action-btn primary-btn" @click="openForm()">
        <span class="material-symbols-outlined icon-g-btn">add</span> 新增配置
      </button>
    </div>

    <div class="header-spacer"></div>

    <div class="config-list">
      <TransitionGroup name="list-fade">
        <div
          v-for="config in configs"
          :key="config.id"
          class="config-card"
          :class="{
            'status-scanning': scanningId === config.id,
            'status-queued': queuedIds.includes(config.id)
          }"
        >
          <div class="card-top">
            <div class="config-identity">
              <h3 class="config-name">{{ config.name }}</h3>
              <span class="status-dot-badge" :class="scanningId === config.id ? 'scanning' : queuedIds.includes(config.id) ? 'queued' : 'idle'">
                {{ scanningId === config.id ? '扫描中...' : queuedIds.includes(config.id) ? '排队中' : '已停止' }}
              </span>
            </div>

            <button
              class="run-toggle-btn"
              :class="scanningId === config.id ? 'scanning' : queuedIds.includes(config.id) ? 'queued' : 'idle'"
              @click="toggleScan(config)"
              :title="scanningId === config.id ? '停止扫描' : queuedIds.includes(config.id) ? '从队列中移除' : '启动扫描'"
            >
              <span v-if="activeIds.includes(config.id)" class="material-symbols-outlined icon-g-toggle">stop</span>
              <span v-else class="material-symbols-outlined icon-g-toggle">play_arrow</span>
            </button>
          </div>

          <div class="card-grid">
            <div class="grid-item">
              <span class="lbl">数据源</span>
              <span class="txt color-blue">{{ dataSourceLabel(config.dataSource) }}</span>
            </div>
            <div class="grid-item">
              <span class="lbl">模板ID</span>
              <span class="txt color-blue">#{{ config.templateId }}</span>
            </div>
            <div class="grid-item full-width">
              <span class="lbl">地区</span>
              <span class="txt color-blue">{{ config.templateRegion || '-' }}</span>
            </div>
            <div class="grid-item full-width">
              <span class="lbl">运营商</span>
              <span class="txt color-blue">{{ config.templateOperator || '-' }}</span>
            </div>
          </div>

          <div class="card-actions" v-show="scanningId !== config.id">
            <button class="text-btn edit" @click="openForm(config)">编辑</button>
            <button
              class="text-btn delete"
              @click="handleDelete(config.id)"
            >
              删除
            </button>
          </div>
        </div>
      </TransitionGroup>

      <div v-if="configs.length === 0" class="empty-state">
        暂无扫描配置，点击右上角新建
      </div>
    </div>

    <div v-if="formState.visible" class="form-overlay" @click="closeForm">
      <div class="form-drawer" @click.stop>
        <div class="drawer-header">
          <h2>{{ formState.isEdit ? '修改配置' : '新增配置' }}</h2>
          <button class="close-x-btn" @click="closeForm">×</button>
        </div>

        <form @submit.prevent="handleSubmit" class="drawer-form">
          <div class="form-item">
            <label>配置名称</label>
            <input v-model="formData.name" type="text" placeholder="如：北京联通-GitHub扫描" required />
          </div>

          <div class="form-item">
            <label>数据源</label>
            <select v-model="formData.dataSource" required>
              <option value="" disabled>选择数据源</option>
              <option v-for="ds in enabledDataSources" :key="ds.value" :value="ds.value">{{ ds.label }}</option>
            </select>
          </div>

          <div class="form-item">
            <label>配置模板</label>
            <select v-model="formData.templateId" required>
              <option value="" disabled>选择模板</option>
              <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
            </select>
          </div>

          <div class="form-item" v-show="formData.dataSource === 'github'">
            <label>GitHub 搜索深度 (页数)</label>
            <div class="input-with-unit">
              <input type="number" v-model.number="formData.searchDepth" min="1" max="30" />
              <span class="unit-text">页</span>
            </div>
          </div>

          <div class="form-buttons">
            <button type="button" class="action-btn cancel-btn" @click="closeForm">取消</button>
            <button type="submit" class="action-btn primary-btn-submit">保存配置</button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import request from '@/api'
import { toast } from '@/components/Toast'
import { useSettingsStore } from '@/stores/settings'
import { useScanConfigStore } from '@/stores/scanConfig'

const scanConfigStore = useScanConfigStore()
const settingsStore = useSettingsStore()

const configs = computed(() => scanConfigStore.configs)
const progress = computed(() => scanConfigStore.progress)

const scanningId = computed(() =>
  progress.value.running ? progress.value.currentId : null
)
const queuedIds = computed(() =>
  progress.value.running ? progress.value.queuedIds : []
)
const activeIds = computed(() => {
  const ids = [...queuedIds.value]
  if (scanningId.value) ids.unshift(scanningId.value)
  return ids
})

// 模板列表
const templates = ref([])

const fetchTemplates = async () => {
  const res = await request.get('/templates')
  templates.value = res
}

const dataSourceLabel = (ds) => {
  const map = { github: 'GitHub', ozone: '零零信安', zoomeye: 'ZoomEye' }
  return map[ds] || ds || '-'
}

// 根据全局设置过滤已启用的数据源
const enabledDataSources = computed(() => {
  const s = settingsStore.data
  const sources = []
  if (!s) return [
    { value: 'github', label: 'GitHub 代码检索' },
    { value: 'ozone', label: '零零信安 空间测绘' },
    { value: 'zoomeye', label: 'ZoomEye 空间测绘' }
  ]
  if (s.github?.enabled !== false) sources.push({ value: 'github', label: 'GitHub 代码检索' })
  if (s.ozone?.enabled !== false) sources.push({ value: 'ozone', label: '零零信安 空间测绘' })
  if (s.zoomeye?.enabled !== false) sources.push({ value: 'zoomeye', label: 'ZoomEye 空间测绘' })
  return sources
})

// 表单状态
const formState = reactive({
  visible: false,
  isEdit: false,
  currentId: null
})

const getDefaultFormData = () => ({
  name: '',
  templateId: '',
  dataSource: 'github',
  searchDepth: 30,
  enabled: true
})

const formData = reactive(getDefaultFormData())

const toggleScan = async (config) => {
  const isActive = activeIds.value.includes(config.id)

  try {
    if (isActive) {
      await request.post(`/configs/${config.id}/stop`)
      toast.info('已停止扫描')
    } else {
      await request.post(`/configs/${config.id}/run`)
      const p = scanConfigStore.progress
      if (p.running) {
        p.queuedIds.push(config.id)
        toast.success('已加入队列')
      } else {
        p.running = true
        p.currentId = config.id
        p.queuedIds = []
        toast.success('扫描任务已启动')
      }
      scanConfigStore.startPolling()
    }
  } catch (e) {
    toast.error(e?.response?.data?.detail || '操作失败')
  }
}

const openForm = (editTarget = null) => {
  if (editTarget) {
    formState.isEdit = true
    formState.currentId = editTarget.id
    Object.assign(formData, {
      name: editTarget.name,
      templateId: editTarget.templateId,
      dataSource: editTarget.dataSource,
      searchDepth: editTarget.searchDepth || 30,
      enabled: editTarget.enabled
    })
  } else {
    formState.isEdit = false
    formState.currentId = null
    Object.assign(formData, getDefaultFormData())
  }
  formState.visible = true
}

const closeForm = () => {
  formState.visible = false
}

const handleSubmit = async () => {
  if (!formData.name?.trim()) { toast.error('配置名称不能为空'); return }
  if (!formData.dataSource) { toast.error('请选择数据源'); return }
  if (!formData.templateId) { toast.error('请选择配置模板'); return }
  if (formData.dataSource === 'github' && (!formData.searchDepth || formData.searchDepth < 1 || formData.searchDepth > 30)) { toast.error('GitHub 搜索深度必须在 1-30 之间'); return }

  try {
    if (formState.isEdit) {
      await request.put(`/configs/${formState.currentId}`, formData)
    } else {
      await request.post('/configs', formData)
    }
    await scanConfigStore.refresh()
    closeForm()
    toast.success('保存成功')
  } catch (e) {
    console.error(e)
    toast.error('保存失败')
  }
}

const handleDelete = async (id) => {
  if (!confirm('确定删除该配置？')) return

  try {
    await request.delete(`/configs/${id}`)
    toast.success('已删除')
    await scanConfigStore.refresh()
  } catch {
    toast.error('删除失败')
  }
}

onMounted(async () => {
  await settingsStore.fetch()

  await scanConfigStore.startPolling()
  await scanConfigStore.fetch()
  await fetchTemplates()
})

onUnmounted(() => {
  scanConfigStore.stopPolling()
})
</script>

<style scoped>
.page-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  background: rgba(245, 245, 247, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 100vw;
}
.header-spacer {
  height: 48px;
  flex-shrink: 0;
}
.action-btn {
  border: none;
  outline: none;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}
.primary-btn {
  background: var(--color-blue);
  color: #FFFFFF;
  padding: 8px 14px;
  border-radius: var(--radius-btn);
  font-size: 13.5px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.primary-btn:active {
  transform: scale(0.96);
  background: #0066D6;
}
.icon-g-btn {
  font-size: 18px !important;
  font-variation-settings: 'FILL' 0, 'wght' 600, 'GRAD' 0, 'opsz' 24;
}

.config-list {
  width: 100%;
  max-width: var(--max-content);
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 90px;
}

.config-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.01);
  display: flex;
  flex-direction: column;
  transition: all 0.3s var(--ease-spring);
}
.config-card.status-scanning {
  border-color: rgba(52, 199, 89, 0.25);
  box-shadow: 0 8px 32px rgba(52, 199, 89, 0.04);
}
.config-card.status-queued {
  border-color: rgba(255, 149, 0, 0.2);
  box-shadow: 0 8px 32px rgba(255, 149, 0, 0.03);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}
.config-identity {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 75%;
}
.config-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}
.status-dot-badge {
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.status-dot-badge::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status-dot-badge.idle { color: var(--text-muted); }
.status-dot-badge.idle::before { background: var(--text-muted); }
.status-dot-badge.scanning { color: var(--color-green); }
.status-dot-badge.scanning::before {
  background: var(--color-green);
  animation: pulse 1.5s infinite;
}
.status-dot-badge.queued { color: var(--color-orange); }
.status-dot-badge.queued::before {
  background: var(--color-orange);
}

.run-toggle-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.run-toggle-btn.idle { background: var(--bg-status-good); color: var(--color-green); }
.run-toggle-btn.scanning { background: var(--bg-status-error); color: var(--color-red); }
.run-toggle-btn.queued { background: var(--bg-status-warn); color: var(--color-orange); }
.run-toggle-btn:active { transform: scale(0.9); }

.card-grid {
  border-top: 1px solid var(--bg-neutral);
  padding-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}
.grid-item { display: flex; align-items: center; gap: 8px; }
.grid-item.full-width { grid-column: span 2; }
.lbl { font-size: 12px; color: var(--text-muted); flex-shrink: 0; width: 48px; }
.txt { font-size: 13.5px; font-weight: 600; }
.color-blue { color: var(--color-blue); }
.color-dark { color: var(--text-primary); }
.color-gray { color: #515154; font-weight: 500; }
.font-mono { font-family: var(--font-mono); letter-spacing: -0.3px; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed var(--bg-neutral);
}
.text-btn {
  background: none; border: none; outline: none;
  font-size: 13px; font-weight: 600; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.text-btn.edit { color: var(--color-blue); }
.text-btn.delete { color: var(--color-red); }

.form-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  z-index: 100;
  display: flex; align-items: flex-end; justify-content: center;
}
.form-drawer {
  background: var(--bg-card); width: 100%; max-width: 420px;
  border-top-left-radius: var(--radius-card); border-top-right-radius: var(--radius-card);
  padding: 24px 24px calc(24px + env(safe-area-inset-bottom)) 24px;
  box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.1);
  animation: slide-up 0.35s var(--ease-spring);
}
.drawer-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.drawer-header h2 { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.close-x-btn {
  background: var(--bg-neutral); border: none; width: 28px; height: 28px;
  border-radius: 50%; font-size: 18px; color: var(--text-muted);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}

.drawer-form input, .drawer-form select {
  appearance: none; -webkit-appearance: none;
  background: var(--bg-neutral); border: none; outline: none;
  padding: 12px; border-radius: var(--radius-input); font-size: 14px;
  font-weight: 500; color: var(--text-primary); width: 100%;
  box-sizing: border-box;
}
.drawer-form select {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%238E8E93' d='M0 0h10L5 6z'/></svg>");
  background-repeat: no-repeat; background-position: right 14px center;
}
.drawer-form input::placeholder { color: var(--text-disabled); }

.form-buttons {
  display: grid; grid-template-columns: 1fr 2fr; gap: 12px;
  margin-top: 12px;
}
.primary-btn-submit {
  background: var(--color-blue);
  color: #FFFFFF;
  padding: 12px;
  border: none;
  border-radius: var(--radius-btn);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
}
.primary-btn-submit:active { transform: scale(0.98); background: #0066D6; }

.cancel-btn {
  background: var(--bg-neutral);
  color: var(--text-muted);
  padding: 12px;
  border-radius: var(--radius-btn);
  font-size: 15px;
  width: 100%;
}
.cancel-btn:active { background: #E8E8ED; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.5; }
  100% { transform: scale(1); opacity: 1; }
}
@keyframes slide-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.list-fade-enter-active, .list-fade-leave-active { transition: all 0.3s var(--ease-spring); }
.list-fade-enter-from, .list-fade-leave-to { opacity: 0; transform: scale(0.93) translateY(12px); }
</style>
