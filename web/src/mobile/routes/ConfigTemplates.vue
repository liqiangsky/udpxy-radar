<template>
  <div class="page-container">

    <div class="page-header">
      <h1 class="page-title">配置模板</h1>
      <button class="action-btn primary-btn" @click="openForm()">
        <span class="material-symbols-outlined icon-g-btn">add</span> 新增模板
      </button>
    </div>

    <div class="header-spacer"></div>

    <div class="template-list">
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 3" :key="i" class="skeleton-card">
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-line skeleton-sub"></div>
          <div class="skeleton-line skeleton-sub narrow"></div>
        </div>
      </div>
      <TransitionGroup v-else name="list-fade">
        <div
          v-for="tpl in templates"
          :key="tpl.id"
          class="template-card"
        >
          <div class="card-top">
            <h3 class="tpl-name">{{ tpl.name }}</h3>
          </div>

          <div class="card-grid">
            <div class="grid-item">
              <span class="lbl">地区</span>
              <span class="txt color-blue">{{ tpl.region }}</span>
            </div>
            <div class="grid-item">
              <span class="lbl">运营商</span>
              <span class="txt color-blue">{{ tpl.operator }}</span>
            </div>
            <div class="grid-item full-width">
              <span class="lbl">目标</span>
              <span class="txt color-dark font-mono">{{ tpl.targetName }}</span>
            </div>
            <div class="grid-item full-width">
              <span class="lbl">地址</span>
              <span class="txt color-gray font-mono truncate" :title="tpl.targetAddress">
                {{ tpl.targetAddress }}
              </span>
            </div>
          </div>

          <div class="card-actions">
            <button class="text-btn edit" @click="openForm(tpl)">编辑</button>
            <button class="text-btn delete" @click="handleDelete(tpl.id)">删除</button>
          </div>
        </div>
      </TransitionGroup>

      <div v-if="!loading && templates.length === 0" class="empty-state">
        暂无模板，点击右上角新建
      </div>
    </div>

    <div v-if="formState.visible" class="form-overlay" @click="closeForm">
      <div class="form-drawer" @click.stop>
        <div class="drawer-header">
          <h2>{{ formState.isEdit ? '修改模板' : '新增模板' }}</h2>
          <button class="close-x-btn" @click="closeForm">×</button>
        </div>

        <form @submit.prevent="handleSubmit" class="drawer-form">
          <div class="form-item">
            <label>模板名称</label>
            <input v-model="formData.name" type="text" placeholder="如：北京联通" required />
          </div>

          <div class="form-row">
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
          </div>

          <div class="form-item">
            <label>目标名称</label>
            <input v-model="formData.targetName" type="text" placeholder="如：CCTV-1 综合" required />
          </div>

          <div class="form-item">
            <label>目标地址（IP段/订阅URL/查询条件）</label>
            <input v-model="formData.targetAddress" type="text" placeholder="rtp://225.1.1.1:1234 或 udpxy country:CN" required />
          </div>

          <div class="form-buttons">
            <button type="button" class="action-btn cancel-btn" @click="closeForm">取消</button>
            <button type="submit" class="action-btn primary-btn-submit">保存模板</button>
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

const formState = reactive({
  visible: false,
  isEdit: false,
  currentId: null
})

const getDefaultFormData = () => ({
  name: '',
  region: '',
  operator: '',
  targetName: '',
  targetAddress: ''
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

const closeForm = () => {
  formState.visible = false
}

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

onMounted(() => {
  fetch()
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

@media (min-width: 768px) {
  .page-header {
    max-width: 720px;
    left: 50%;
    transform: translateX(-50%);
  }
}
@media (min-width: 1024px) {
  .page-header { max-width: 1100px; }
}
@media (min-width: 1440px) {
  .page-header { max-width: 1400px; }
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

.template-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  width: 100%;
  max-width: var(--max-content);
  padding-bottom: 90px;
}

@media (min-width: 768px) {
  .template-list { max-width: 720px; }
}
@media (min-width: 1024px) {
  .template-list { max-width: 1100px; }
}
@media (min-width: 1440px) {
  .template-list { max-width: 1400px; }
}

.template-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.01);
  display: flex;
  flex-direction: column;
  transition: all 0.3s var(--ease-spring);
}

.card-top {
  margin-bottom: 14px;
}
.tpl-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.card-grid {
  border-top: 1px solid var(--bg-neutral);
  padding-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}
.grid-item { display: flex; align-items: center; gap: 8px; }
.grid-item.full-width { grid-column: span 2; }
.lbl { font-size: 12px; color: var(--text-muted); flex-shrink: 0; width: 38px; }
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

@keyframes slide-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

/* 骨架屏 */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 90px;
}
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.skeleton-line {
  height: 16px;
  border-radius: 8px;
  background: linear-gradient(90deg, var(--bg-neutral) 25%, #E8E8ED 50%, var(--bg-neutral) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
}
.skeleton-title { width: 60%; }
.skeleton-sub { width: 40%; }
.skeleton-sub.narrow { width: 25%; }
@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.list-fade-enter-active, .list-fade-leave-active { transition: all 0.3s var(--ease-spring); }
.list-fade-enter-from, .list-fade-leave-to { opacity: 0; transform: scale(0.93) translateY(12px); }
</style>
