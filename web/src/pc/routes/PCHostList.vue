<template>
  <div class="pc-page">
    <div class="pc-page-header">
      <h1 class="pc-page-title">组播源</h1>
      <div class="header-filters">
        <select v-model="filterForm.region" class="pc-select">
          <option value="">全部地区</option>
          <option v-for="opt in regions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        <select v-model="filterForm.operator" class="pc-select">
          <option value="">全部网络</option>
          <option v-for="opt in operators" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        <span class="filter-count"><span>{{ filteredList.length }}</span> 个可用</span>
      </div>
    </div>

    <!-- Skeleton -->
    <div v-if="loading" class="card-grid">
      <div v-for="i in 8" :key="i" class="skeleton-card">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-sub"></div>
      </div>
    </div>

    <!-- Card Grid -->
    <TransitionGroup v-else name="card-fade" tag="div" class="card-grid">
      <IptvHostCard
        v-for="source in filteredList"
        :key="source.id"
        :item="source"
        @copy="handleCopy"
        @test="handleTestDelay"
      />
    </TransitionGroup>

    <div v-if="!loading && filteredList.length === 0" class="empty-state">
      <p>暂无符合当前筛选条件的组播源</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import request from '@/api'
import IptvHostCard from '@/components/HostCard.vue'
import { regions, operators } from '@/data.js'
import { toast } from '@/components/Toast'

const filterForm = reactive({ region: '', operator: '' })
const rawIptvList = ref([])
const loading = ref(false)
const regionMap = reactive({})
const operatorMap = reactive({})

const loadPool = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterForm.region) params.region = filterForm.region
    if (filterForm.operator) params.operator = filterForm.operator
    const res = await request.get('/iptv-pool', { params })
    const flatList = []
    res.groups.forEach(group => {
      group.heads.forEach(item => {
        flatList.push({
          id: item.id,
          host: item.host,
          delay: item.latencyMs,
          region: item.region,
          operator: item.operator,
          geoRegion: item.geoRegion,
          geoOperator: item.geoOperator,
          playUrl: item.url,
          protocol: item.protocol,
          target: item.target,
          channelName: item.channelName,
          createTime: item.createTime,
          lastSeen: item.lastSeen,
          sourceType: item.sourceType,
          sourceName: item.sourceName,
        })
        if (item.region) regionMap[item.region] = item.region
        if (item.operator) operatorMap[item.operator] = item.operator
      })
    })
    rawIptvList.value = flatList
  } catch (e) {
    console.error('加载组播池失败:', e)
  } finally {
    loading.value = false
  }
}

const filteredList = computed(() => {
  return rawIptvList.value.filter(item => {
    const matchRegion = !filterForm.region || item.region === filterForm.region
    const matchOperator = !filterForm.operator || item.operator === filterForm.operator
    return matchRegion && matchOperator
  })
})

const handleCopy = async (host) => {
  try {
    await navigator.clipboard.writeText(host)
    toast.success(`HOST 已复制: ${host}`)
  } catch {
    toast.error('复制失败')
  }
}

const handleTestDelay = async (item) => {
  try {
    const res = await request.post(`/iptv/${item.id}/test-delay`)
    if (res.ok) {
      item.delay = res.delay
      toast.success(`延迟: ${res.delay}ms`)
    } else {
      item.delay = -1
      toast.warning('超时或不可达')
    }
  } catch {
    item.delay = -1
    toast.error('测试失败')
  }
}

onMounted(() => {
  loadPool()
})
</script>

<style scoped>
@import '../pc.css';

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.header-filters {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pc-select {
  appearance: none;
  -webkit-appearance: none;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid rgba(0, 0, 0, 0.06);
  padding: 8px 36px 8px 12px;
  border-radius: var(--radius-input);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%238E8E93' d='M0 0h10L5 6z'/></svg>");
  background-repeat: no-repeat;
  background-position: right 12px center;
  transition: all 0.15s ease;
  box-shadow: var(--shadow-sm);
}

.pc-select:hover {
  border-color: var(--color-blue);
}

.pc-select:focus {
  border-color: var(--color-blue);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
}

.filter-count {
  font-size: 13px;
  color: var(--text-muted);
  margin-left: 4px;
}

.filter-count span {
  color: var(--color-green);
  font-weight: 700;
}

/* Skeleton */
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-sm);
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

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Transition */
.card-fade-enter-active,
.card-fade-leave-active {
  transition: all 0.3s var(--ease-spring);
}

.card-fade-enter-from,
.card-fade-leave-to {
  opacity: 0;
  transform: scale(0.92) translateY(10px);
}
</style>
