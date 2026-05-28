<template>
  <div class="pc-page">
    <div class="pc-page-header">
      <h1 class="pc-page-title">扫描配置</h1>
      <button class="pc-primary-btn" @click="openForm()">
        <span class="material-symbols-outlined" style="font-size: 18px !important">add</span>
        新增配置
      </button>
    </div>

    <!-- Skeleton -->
    <div v-if="!scanConfigStore.loaded" class="pc-skeleton-list">
      <div v-for="i in 3" :key="i" class="pc-skeleton-row">
        <div class="pc-skeleton-cell" style="width: 140px"></div>
        <div class="pc-skeleton-cell" style="width: 160px"></div>
        <div class="pc-skeleton-cell" style="width: 80px"></div>
        <div class="pc-skeleton-cell" style="width: 80px"></div>
        <div class="pc-skeleton-cell" style="width: 80px"></div>
        <div class="pc-skeleton-cell" style="width: 100px"></div>
        <div class="pc-skeleton-cell" style="width: 120px"></div>
      </div>
    </div>

    <!-- Data Table -->
    <table v-else class="pc-data-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>数据源</th>
          <th style="width: 80px">模板ID</th>
          <th style="width: 90px">地区</th>
          <th style="width: 90px">运营商</th>
          <th style="width: 100px">状态</th>
          <th style="width: 130px">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="config in configs"
          :key="config.id"
          :class="{
            'row-scanning': scanningId === config.id,
            'row-queued': queuedIds.includes(config.id)
          }"
        >
          <td class="name-cell">{{ config.name }}</td>
          <td class="source-cell">{{ dataSourceLabel(config.dataSource) }}</td>
          <td class="mono-cell">#{{ config.templateId }}</td>
          <td>{{ config.templateRegion || '-' }}</td>
          <td>{{ config.templateOperator || '-' }}</td>
          <td>
            <span class="pc-status-badge" :class="scanningId === config.id ? 'scanning' : queuedIds.includes(config.id) ? 'queued' : 'idle'">
              <span class="pc-status-dot"></span>
              {{ scanningId === config.id ? '扫描中' : queuedIds.includes(config.id) ? '排队中' : '已停止' }}
            </span>
          </td>
          <td>
            <div class="action-group">
              <button
                class="pc-run-btn"
                :class="scanningId === config.id ? 'stop' : queuedIds.includes(config.id) ? 'queue' : 'run'"
                @click="toggleScan(config)"
                :title="scanningId === config.id ? '停止扫描' : queuedIds.includes(config.id) ? '从队列中移除' : '启动扫描'"
              >
                <span class="material-symbols-outlined" style="font-size: 18px !important">
                  {{ activeIds.includes(config.id) ? 'stop' : 'play_arrow' }}
                </span>
              </button>
              <button
                v-show="scanningId !== config.id"
                class="pc-action-btn edit"
                @click="openForm(config)"
                title="编辑"
              >
                <span class="material-symbols-outlined" style="font-size: 18px !important">edit</span>
              </button>
              <button
                v-show="scanningId !== config.id"
                class="pc-action-btn delete"
                @click="handleDelete(config.id)"
                title="删除"
              >
                <span class="material-symbols-outlined" style="font-size: 18px !important">delete</span>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="scanConfigStore.loaded && configs.length === 0" class="empty-state">
      <p>暂无扫描配置，点击"新增配置"创建</p>
    </div>

    <!-- Modal -->
    <div v-if="formState.visible" class="pc-modal-overlay" @click="closeForm">
      <div class="pc-modal" @click.stop>
        <div class="pc-modal-header">
          <h2 class="pc-modal-title">{{ formState.isEdit ? '修改配置' : '新增配置' }}</h2>
          <button class="pc-modal-close" @click="closeForm">&times;</button>
        </div>

        <form @submit.prevent="handleSubmit">
          <div class="pc-form-grid">
            <div class="form-item full-width">
              <label>配置名称</label>
              <input v-model="formData.name" type="text" placeholder="如：北京联通-GitHub扫描" required />
            </div>

            <div class="form-item full-width">
              <label>数据源</label>
              <div class="pc-source-tags">
                <label class="pc-source-tag" :class="{ active: formData.dataSources.length === 0 }">
                  <input type="checkbox" :checked="formData.dataSources.length === 0" @change="toggleAllSources" />
                  全部
                </label>
                <label
                  v-for="ds in enabledDataSources"
                  :key="ds.value"
                  class="pc-source-tag"
                  :class="{ active: formData.dataSources.includes(ds.value) }"
                >
                  <input
                    type="checkbox"
                    :value="ds.value"
                    :checked="formData.dataSources.includes(ds.value)"
                    @change="toggleSource(ds.value)"
                  />
                  {{ ds.label }}
                </label>
              </div>
              <p class="field-hint">不选表示扫描全部启用的数据源</p>
            </div>

            <div class="form-item full-width">
              <label>配置模板</label>
              <select v-model="formData.templateId" required>
                <option value="" disabled>选择模板</option>
                <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
              </select>
            </div>

            <div v-if="formData.dataSources.length === 0 || formData.dataSources.includes('github')" class="form-item full-width">
              <label>GitHub 搜索深度（页数）</label>
              <input type="number" v-model.number="formData.searchDepth" min="1" max="30" />
            </div>
          </div>

          <div class="pc-modal-footer">
            <button type="button" class="pc-btn-outline" @click="closeForm">取消</button>
            <button type="submit" class="pc-primary-btn">保存</button>
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

const scanningId = computed(() => progress.value.running ? progress.value.currentId : null)
const queuedIds = computed(() => progress.value.running ? progress.value.queuedIds : [])
const activeIds = computed(() => {
  const ids = [...queuedIds.value]
  if (scanningId.value) ids.unshift(scanningId.value)
  return ids
})

const templates = ref([])
const fetchTemplates = async () => {
  const res = await request.get('/templates')
  templates.value = res
}

const dataSourceLabel = (ds) => {
  const map = { github: 'GitHub', ozone: '零零信安', zoomeye: 'ZoomEye', daydaymap: 'DayDayMap', hunter: 'Hunter' }
  if (!ds) return '全部'
  return ds.split(',').filter(Boolean).map(d => map[d] || d).join(' / ')
}

const toggleSource = (val) => {
  const idx = formData.dataSources.indexOf(val)
  if (idx >= 0) formData.dataSources.splice(idx, 1)
  else formData.dataSources.push(val)
}

const toggleAllSources = () => { formData.dataSources = [] }

const enabledDataSources = computed(() => {
  const s = settingsStore.data
  const sources = []
  if (!s) return [
    { value: 'github', label: 'GitHub 代码检索' },
    { value: 'ozone', label: '零零信安 空间测绘' },
    { value: 'zoomeye', label: 'ZoomEye 空间测绘' },
    { value: 'daydaymap', label: 'DayDayMap 空间测绘' },
    { value: 'hunter', label: 'Hunter 空间测绘' }
  ]
  if (s.github?.enabled !== false) sources.push({ value: 'github', label: 'GitHub 代码检索' })
  if (s.ozone?.enabled !== false) sources.push({ value: 'ozone', label: '零零信安 空间测绘' })
  if (s.zoomeye?.enabled !== false) sources.push({ value: 'zoomeye', label: 'ZoomEye 空间测绘' })
  if (s.daydaymap?.enabled !== false) sources.push({ value: 'daydaymap', label: 'DayDayMap 空间测绘' })
  if (s.hunter?.enabled !== false) sources.push({ value: 'hunter', label: 'Hunter 空间测绘' })
  return sources
})

const formState = reactive({ visible: false, isEdit: false, currentId: null })

const getDefaultFormData = () => ({
  name: '', templateId: '', dataSources: [], dataSource: '', searchDepth: 30, enabled: true
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
    const rawDs = editTarget.dataSource || ''
    Object.assign(formData, {
      name: editTarget.name,
      templateId: editTarget.templateId,
      dataSources: rawDs ? rawDs.split(',').filter(Boolean) : [],
      dataSource: rawDs,
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

const closeForm = () => { formState.visible = false }

const handleSubmit = async () => {
  if (!formData.name?.trim()) { toast.error('配置名称不能为空'); return }
  if (!formData.templateId) { toast.error('请选择配置模板'); return }
  if ((formData.dataSources.length === 0 || formData.dataSources.includes('github')) && (!formData.searchDepth || formData.searchDepth < 1 || formData.searchDepth > 30)) {
    toast.error('GitHub 搜索深度必须在 1-30 之间'); return
  }

  const payload = { ...formData, dataSource: formData.dataSources.join(',') }
  delete payload.dataSources

  try {
    if (formState.isEdit) {
      await request.put(`/configs/${formState.currentId}`, payload)
    } else {
      await request.post('/configs', payload)
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

onUnmounted(() => { scanConfigStore.stopPolling() })
</script>

<style scoped>
@import '../pc.css';

.name-cell { font-weight: 700; }

.source-cell { font-size: 12px; color: var(--color-blue); font-weight: 600; }

.mono-cell { font-family: var(--font-mono); }

.row-scanning {
  border-left: 3px solid #34c759;
}

.row-queued {
  border-left: 3px solid #ff9500;
}

.action-group {
  display: flex;
  gap: 4px;
  align-items: center;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
  margin-bottom: 0;
}

.pc-skeleton-list {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.pc-skeleton-row {
  display: flex;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--bg-neutral);
  align-items: center;
}
</style>
