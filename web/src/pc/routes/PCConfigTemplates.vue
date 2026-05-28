<template>
  <div class="pc-page">
    <div class="pc-page-header">
      <h1 class="pc-page-title">配置模板</h1>
      <button class="pc-primary-btn" @click="openForm()">
        <span class="material-symbols-outlined" style="font-size: 18px !important">add</span>
        新增模板
      </button>
    </div>

    <!-- Skeleton -->
    <div v-if="loading" class="pc-skeleton-list">
      <div v-for="i in 3" :key="i" class="pc-skeleton-row">
        <div class="pc-skeleton-cell" style="width: 120px"></div>
        <div class="pc-skeleton-cell" style="width: 80px"></div>
        <div class="pc-skeleton-cell" style="width: 80px"></div>
        <div class="pc-skeleton-cell" style="width: 120px"></div>
        <div class="pc-skeleton-cell" style="width: 200px"></div>
        <div class="pc-skeleton-cell" style="width: 100px"></div>
      </div>
    </div>

    <!-- Data Table -->
    <table v-else class="pc-data-table">
      <thead>
        <tr>
          <th>名称</th>
          <th style="width: 90px">地区</th>
          <th style="width: 90px">运营商</th>
          <th>目标名称</th>
          <th>目标地址</th>
          <th style="width: 100px">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="tpl in templates" :key="tpl.id">
          <td class="name-cell">{{ tpl.name }}</td>
          <td>{{ tpl.region }}</td>
          <td>{{ tpl.operator }}</td>
          <td class="mono-cell">{{ tpl.targetName }}</td>
          <td class="addr-cell" :title="tpl.targetAddress">{{ tpl.targetAddress }}</td>
          <td>
            <div class="action-group">
              <button class="pc-action-btn edit" @click="openForm(tpl)" title="编辑">
                <span class="material-symbols-outlined" style="font-size: 18px !important">edit</span>
              </button>
              <button class="pc-action-btn delete" @click="handleDelete(tpl.id)" title="删除">
                <span class="material-symbols-outlined" style="font-size: 18px !important">delete</span>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="!loading && templates.length === 0" class="empty-state">
      <p>暂无模板，点击"新增模板"创建</p>
    </div>

    <!-- Modal -->
    <div v-if="formState.visible" class="pc-modal-overlay" @click="closeForm">
      <div class="pc-modal" @click.stop>
        <div class="pc-modal-header">
          <h2 class="pc-modal-title">{{ formState.isEdit ? '修改模板' : '新增模板' }}</h2>
          <button class="pc-modal-close" @click="closeForm">&times;</button>
        </div>

        <form @submit.prevent="handleSubmit">
          <div class="pc-form-grid">
            <div class="form-item full-width">
              <label>模板名称</label>
              <input v-model="formData.name" type="text" placeholder="如：北京联通" required />
            </div>

            <div class="form-item">
              <label>地区</label>
              <select v-model="formData.region" required>
                <option value="" disabled>选择地区</option>
                <option v-for="(name, id) in regions" :key="id" :value="name">{{ name }}</option>
              </select>
            </div>

            <div class="form-item">
              <label>运营商</label>
              <select v-model="formData.operator" required>
                <option value="" disabled>选择运营商</option>
                <option v-for="(name, id) in operators" :key="id" :value="name">{{ name }}</option>
              </select>
            </div>

            <div class="form-item full-width">
              <label>目标名称</label>
              <input v-model="formData.targetName" type="text" placeholder="如：CCTV-1 综合" required />
            </div>

            <div class="form-item full-width">
              <label>目标地址（IP段/订阅URL/查询条件）</label>
              <input v-model="formData.targetAddress" type="text" placeholder="rtp://225.1.1.1:1234 或 udpxy country:CN" required />
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
import { ref, reactive, onMounted } from 'vue'
import request from '@/api'
import { regions, operators } from '@/data.js'
import { toast } from '@/components/Toast'

const templates = ref([])
const loading = ref(false)

const formState = reactive({ visible: false, isEdit: false, currentId: null })

const getDefaultFormData = () => ({
  name: '', region: '', operator: '', targetName: '', targetAddress: ''
})

const formData = reactive(getDefaultFormData())

const fetch = async () => {
  loading.value = true
  try {
    const res = await request.get('/templates')
    templates.value = res
  } finally {
    loading.value = false
  }
}

const openForm = (editTarget = null) => {
  if (editTarget) {
    formState.isEdit = true
    formState.currentId = editTarget.id
    Object.assign(formData, editTarget)
  } else {
    formState.isEdit = false
    formState.currentId = null
    Object.assign(formData, getDefaultFormData())
  }
  formState.visible = true
}

const closeForm = () => { formState.visible = false }

const handleSubmit = async () => {
  if (!formData.name?.trim()) { toast.error('模板名称不能为空'); return }
  if (!formData.region) { toast.error('请选择地区'); return }
  if (!formData.operator) { toast.error('请选择运营商'); return }
  if (!formData.targetName?.trim()) { toast.error('目标名称不能为空'); return }
  if (!formData.targetAddress?.trim()) { toast.error('目标地址不能为空'); return }

  try {
    if (formState.isEdit) {
      await request.put(`/templates/${formState.currentId}`, formData)
    } else {
      await request.post('/templates', formData)
    }
    await fetch()
    closeForm()
    toast.success('保存成功')
  } catch (e) {
    console.error(e)
    toast.error('保存失败')
  }
}

const handleDelete = async (id) => {
  if (!confirm('确定删除该模板？')) return
  try {
    await request.delete(`/templates/${id}`)
    toast.success('已删除')
    await fetch()
  } catch {
    toast.error('删除失败')
  }
}

onMounted(() => { fetch() })
</script>

<style scoped>
@import '../pc.css';

.name-cell {
  font-weight: 700;
  color: var(--text-primary);
}

.mono-cell {
  font-family: var(--font-mono);
  font-size: 13px;
}

.addr-cell {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-group {
  display: flex;
  gap: 4px;
}

.pc-primary-btn {
  background: var(--color-blue);
  color: #fff;
  border: none;
  padding: 10px 18px;
  border-radius: var(--radius-btn);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
}

.pc-primary-btn:active { transform: scale(0.96); background: #0066D6; }

.pc-btn-outline {
  background: var(--bg-neutral);
  color: var(--text-secondary);
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-btn);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pc-btn-outline:active { background: #E8E8ED; }

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
