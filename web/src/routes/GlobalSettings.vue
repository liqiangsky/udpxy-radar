<template>
  <div class="page-container">

    <div class="page-header">
      <h1 class="page-title">全局设置</h1>
      <button class="save-btn" @click="handleSave">
        <span class="material-symbols-outlined save-btn-icon">save</span>
        <span>{{ saving ? '保存中...' : '保存' }}</span>
      </button>
    </div>

    <div class="header-spacer"></div>

    <div class="settings-flow">

      <!-- GitHub 数据源 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">code</span>
          <h2>GitHub 代码检索</h2>
          <label class="toggle-switch">
            <input type="checkbox" v-model="settings.github.enabled" />
            <span class="slider"></span>
          </label>
        </div>

        <div class="form-group">
          <label>GitHub Personal Token</label>
          <div class="input-with-icon">
            <span class="material-symbols-outlined input-prefix">key</span>
            <input
              v-model="settings.github.token"
              type="password"
              placeholder="ghp_****************************"
            />
          </div>
          <p class="field-desc">用于解除 GitHub API 速率限制，提高组播源检索成功率。</p>
        </div>

        <div class="form-group">
          <label>UserResult 自定义搜索关键词</label>
          <input
            v-model="settings.github.userResultQuery"
            type="text"
            class="input-base"
            placeholder="filename:result.txt path:output/ipv4"
          />
          <p class="field-desc">GitHub Code Search 关键词，用于搜索文件。留空使用默认搜索。</p>
        </div>

        <div class="form-group">
          <label>UserResult 自定义 URL 列表</label>
          <textarea
            v-model="settings.github.userResultUrls"
            class="input-base textarea-input"
            rows="4"
          ></textarea>
          <p class="field-desc">一行一个完整 raw URL，直接下载解析，不走搜索 API。</p>
        </div>

        <div class="form-group">
          <label>UserResult 定时拉取 (Cron)</label>
          <input
            v-model="settings.github.userResultFetchCron"
            type="text"
            class="input-base"
            placeholder="留空表示不执行"
          />
          <p class="field-desc">定时从 GitHub 拉取直播源。搜索使用上方关键词，URL 列表使用上方配置。留空不执行。</p>
        </div>

        <div class="form-group">
          <label>手动拉取测试</label>
          <button
            class="fetch-btn-mini"
            :class="{ fetching: githubUserResultFetching }"
            @click="handleGitHubUserResultFetch"
          >
            <span class="material-symbols-outlined fetch-icon" :class="{ spin: githubUserResultFetching }">cloud_download</span>
            <span>{{ githubUserResultFetching ? '拉取中' : '拉取 UserResult 源数据' }}</span>
          </button>
          <p class="field-desc" v-if="githubUserResultResult">获取到 {{ githubUserResultResult }} 条可用数据，已写入 source_cache</p>
        </div>
      </div>

      <!-- 零零信安 数据源 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">public</span>
          <h2>零零信安 空间测绘</h2>
          <label class="toggle-switch">
            <input type="checkbox" v-model="settings.ozone.enabled" />
            <span class="slider"></span>
          </label>
        </div>

        <div class="form-group">
          <label>定时拉取 (Cron)</label>
          <input
            v-model="settings.ozone.fetchCron"
            type="text"
            class="input-base"
            placeholder="留空表示不执行"
          />
          <p class="field-desc">从 零零信安 拉取数据的定时任务 Cron 表达式。留空不执行。</p>
        </div>

        <div class="form-group">
          <label>手动拉取测试</label>
          <button
            class="fetch-btn-mini"
            :class="{ fetching: fetching }"
            @click="handleManualFetch"
          >
            <span class="material-symbols-outlined fetch-icon" :class="{ spin: fetching }">cloud_download</span>
            <span>{{ fetching ? '拉取中' : '拉取 零零信安 源数据' }}</span>
          </button>
          <p class="field-desc" v-if="ozoneResult">获取到 {{ ozoneResult }} 条数据，已写入 source_cache</p>
          <p class="field-desc">固定搜索词: udpxy multicast UDP-to-HTTP</p>
        </div>
      </div>

      <!-- zoomeye 数据源 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">radar</span>
          <h2>ZoomEye 空间测绘</h2>
          <label class="toggle-switch">
            <input type="checkbox" v-model="settings.zoomeye.enabled" />
            <span class="slider"></span>
          </label>
        </div>

        <div class="form-group">
          <label>定时拉取 (Cron)</label>
          <input
            v-model="settings.zoomeye.fetchCron"
            type="text"
            class="input-base"
            placeholder="留空表示不执行"
          />
          <p class="field-desc">触发 GitHub Action 的定时任务 Cron 表达式。留空不执行。</p>
        </div>

        <div class="form-group">
          <label>手动拉取测试</label>
          <button
            class="fetch-btn-mini"
            :class="{ fetching: zoomeyeFetching }"
            @click="handleZoomeyeManualFetch"
          >
            <span class="material-symbols-outlined fetch-icon" :class="{ spin: zoomeyeFetching }">cloud_download</span>
            <span>{{ zoomeyeFetching ? '触发中' : '触发 ZoomEye 数据拉取' }}</span>
          </button>
          <p class="field-desc" v-show="zoomeyeResult">已触发，等待 GitHub Action 回调推送</p>
          <p class="field-desc">未登录账号只能查看第一页结果。</p>
        </div>
      </div>

      <!-- DayDayMap 数据源 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">map</span>
          <h2>DayDayMap 空间测绘</h2>
          <label class="toggle-switch">
            <input type="checkbox" v-model="settings.daydaymap.enabled" />
            <span class="slider"></span>
          </label>
        </div>

        <div class="form-group">
          <label>定时拉取 (Cron)</label>
          <input
            v-model="settings.daydaymap.fetchCron"
            type="text"
            class="input-base"
            placeholder="留空表示不执行"
          />
          <p class="field-desc">从 DayDayMap 拉取数据的定时任务 Cron 表达式。留空不执行。</p>
        </div>

        <div class="form-group">
          <label>手动拉取测试</label>
          <button
            class="fetch-btn-mini"
            :class="{ fetching: daydaymapFetching }"
            @click="handleDaydaymapManualFetch"
          >
            <span class="material-symbols-outlined fetch-icon" :class="{ spin: daydaymapFetching }">cloud_download</span>
            <span>{{ daydaymapFetching ? '拉取中' : '拉取 DayDayMap 源数据' }}</span>
          </button>
          <p class="field-desc" v-if="daydaymapResult">获取到 {{ daydaymapResult }} 条数据，已写入 source_cache</p>
          <p class="field-desc">固定搜索词: product="Udpxy Web Module"，未登录只能查看第一页结果。</p>
        </div>
      </div>

      <!-- Hunter 数据源 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">radar</span>
          <h2>Hunter 空间测绘</h2>
          <label class="toggle-switch">
            <input type="checkbox" v-model="settings.hunter.enabled" />
            <span class="slider"></span>
          </label>
        </div>

        <div class="form-group">
          <label>API Key</label>
          <div class="input-with-icon">
            <span class="material-symbols-outlined input-prefix">key</span>
            <input
              v-model="settings.hunter.apiKey"
              type="password"
              placeholder="hunter API Key"
            />
          </div>
          <p class="field-desc">奇安信 Hunter API Key，用于解除速率限制。</p>
        </div>

        <div class="form-group">
          <label>定时拉取 (Cron)</label>
          <input
            v-model="settings.hunter.fetchCron"
            type="text"
            class="input-base"
            placeholder="留空表示不执行"
          />
          <p class="field-desc">从 Hunter 拉取数据的定时任务 Cron 表达式。留空不执行。</p>
        </div>

        <div class="form-group">
          <label>手动拉取测试</label>
          <button
            class="fetch-btn-mini"
            :class="{ fetching: hunterFetching }"
            @click="handleHunterManualFetch"
          >
            <span class="material-symbols-outlined fetch-icon" :class="{ spin: hunterFetching }">cloud_download</span>
            <span>{{ hunterFetching ? '拉取中' : '拉取 Hunter 源数据' }}</span>
          </button>
          <p class="field-desc" v-if="hunterResult">获取到 {{ hunterResult }} 条数据，已写入 source_cache</p>
          <p class="field-desc">固定搜索词: header="Server: udpxy"&&ip.country=="中国"</p>
        </div>
      </div>

      <!-- 扫描引擎参数 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">speed</span>
          <h2>扫描引擎参数</h2>
        </div>

        <div class="form-grid-2">
          <div class="form-group">
            <label>并发验证数</label>
            <div class="input-with-unit">
              <input
                v-model.number="settings.engine.concurrency"
                type="number"
                min="1"
                max="500"
              />
              <span class="unit-text">线程</span>
            </div>
          </div>

          <div class="form-group">
            <label>连接超时</label>
            <div class="input-with-unit">
              <input
                v-model.number="settings.engine.timeout"
                type="number"
                min="200"
                max="10000"
                step="100"
              />
              <span class="unit-text">ms</span>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>配置间延迟 (Delay)</label>
          <div class="input-with-unit">
            <input
              v-model.number="settings.engine.configDelay"
              type="number"
              min="0"
              max="60"
            />
            <span class="unit-text">秒</span>
          </div>
          <p class="field-desc">上一个扫描配置结束后，队列进入下一个配置前的等待缓冲时间。</p>
        </div>
      </div>

      <!-- 自动化调度 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">schedule</span>
          <h2>自动化调度</h2>
        </div>

        <div class="form-group">
          <label>定时扫描 (Cron)</label>
          <input
            v-model="settings.scheduling.scanCron"
            type="text"
            class="input-base"
            placeholder="留空表示不执行"
          />
          <p class="field-desc">Cron 表达式：分 时 日 月 周。留空不执行。统一调度所有数据源扫描。</p>
        </div>

        <div class="form-group">
          <label>定时复测 (Cron)</label>
          <input
            v-model="settings.scheduling.janitorCron"
            type="text"
            class="input-base"
            placeholder="留空表示不执行"
          />
          <p class="field-desc">Cron 表达式：分 时 日 月 周。留空不执行。</p>
        </div>

        <div class="cron-help">
          <details>
            <summary>📖 Cron 表达式帮助</summary>
            <div class="help-content">
              <p><b>格式</b>：分 时 日 月 周（5 个字段，空格分隔）</p>
              <p><b>取值范围</b>：</p>
              <table>
                <tbody>
                  <tr><td>分</td><td>0-59</td></tr>
                  <tr><td>时</td><td>0-23</td></tr>
                  <tr><td>日</td><td>1-31</td></tr>
                  <tr><td>月</td><td>1-12</td></tr>
                  <tr><td>周</td><td>1-7（1=周一，7=周日）</td></tr>
                </tbody>
              </table>
              <p><b>常用符号</b>：</p>
              <p><code>*</code> 表示任意值</p>
              <p><code>/</code> 表示步长，如 <code>*/10</code> 表示每 10 分钟</p>
              <p><code>-</code> 表示范围，如 <code>9-17</code> 表示 9 到 17 点</p>
              <p><code>,</code> 表示多个值，如 <code>8,12,18</code> 表示 8、12、18 点</p>
              <p><b>常用示例</b>：</p>
              <p><code>0 2 * * *</code> → 每天凌晨 2:00</p>
              <p><code>*/30 * * * *</code> → 每 30 分钟</p>
              <p><code>0 */4 * * *</code> → 每 4 小时整点</p>
              <p><code>0 9 * * 1-5</code> → 工作日 9:00</p>
              <p><code>0 3 * * 1</code> → 每周一 3:00</p>
            </div>
          </details>
        </div>
      </div>

      <!-- 安全认证 -->
      <div class="settings-card">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">lock</span>
          <h2>安全认证</h2>
        </div>

        <div class="form-group">
          <label>API 认证 Token</label>
          <input
            v-model="settings.security.callbackToken"
            type="text"
            class="input-base"
            placeholder="留空表示不启用认证"
          />
          <p class="field-desc">设置后，所有写操作需携带 X-Callback-Token 请求头。CF Worker 和 GitHub Action 需同步配置。</p>
        </div>
      </div>

      <!-- 后台日志入口 -->
      <div class="settings-card logs-entry-card" @click="$router.push('/logs')">
        <div class="card-title-group">
          <span class="material-symbols-outlined card-icon">receipt_long</span>
          <h2>后台日志</h2>
          <span class="material-symbols-outlined entry-arrow">chevron_right</span>
        </div>
        <p class="field-desc">查看实时运行日志，支持按级别筛选</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { toast } from '@/components/Toast'
import { useSettingsStore } from '@/stores/settings'
import request from '@/api'

const settingsStore = useSettingsStore()

const fetching = ref(false)
const ozoneResult = ref(0)

const handleManualFetch = async () => {
  if (!settings.ozone.enabled) {
    toast.warning('请先启用 零零信安 数据源')
    return
  }
  fetching.value = true
  try {
    const res = await request.post('/ozone/fetch')
    ozoneResult.value = res.fetched
    toast.success(`拉取成功：获取到 ${res.fetched} 条数据`)
  } catch (e) {
    toast.error(e?.response?.data?.detail || '拉取失败')
  } finally {
    fetching.value = false
  }
}

const githubUserResultFetching = ref(false)
const githubUserResultResult = ref(0)

const handleGitHubUserResultFetch = async () => {
  if (!settings.github.enabled) {
    toast.warning('请先启用 GitHub 数据源')
    return
  }
  githubUserResultFetching.value = true
  try {
    const urls = settings.github.userResultUrls
      .split('\n')
      .map(u => u.trim())
      .filter(u => u.startsWith('https://'))
    const res = await request.post('/github-user-result/fetch', {
      query: settings.github.userResultQuery,
      urls: urls
    })
    githubUserResultResult.value = res.fetched
    toast.success(`拉取成功：获取到 ${res.fetched} 条数据`)
  } catch (e) {
    toast.error(e?.response?.data?.detail || '拉取失败')
  } finally {
    githubUserResultFetching.value = false
  }
}

const settings = reactive({
  github: { enabled: true, token: '', userResultQuery: '', userResultFetchCron: '', userResultUrls: '' },
  ozone: { enabled: false, fetchCron: '' },
  zoomeye: { enabled: false, fetchCron: '' },
  daydaymap: { enabled: false, fetchCron: '' },
  hunter: { enabled: false, apiKey: '', fetchCron: '' },
  engine: { concurrency: 64, timeout: 2000, configDelay: 3 },
  scheduling: { scanCron: '', janitorCron: '' },
  security: { callbackToken: '' }
})

const saving = ref(false)

const loadSettings = async () => {
  const res = await settingsStore.fetch()
  if (res.github) Object.assign(settings.github, res.github)
  if (res.ozone) Object.assign(settings.ozone, res.ozone)
  if (res.zoomeye) Object.assign(settings.zoomeye, res.zoomeye)
  if (res.daydaymap) Object.assign(settings.daydaymap, res.daydaymap)
  if (res.hunter) Object.assign(settings.hunter, res.hunter)
  if (res.engine) Object.assign(settings.engine, res.engine)
  if (res.scheduling) Object.assign(settings.scheduling, res.scheduling)
  if (res.security) Object.assign(settings.security, res.security)
}

const zoomeyeFetching = ref(false)
const zoomeyeResult = ref(false)

const handleZoomeyeManualFetch = async () => {
  if (!settings.zoomeye.enabled) {
    toast.warning('请先启用 ZoomEye 数据源')
    return
  }
  zoomeyeFetching.value = true
  try {
    await request.post('/zoomeye/fetch')
    zoomeyeResult.value = true
    toast.success('已触发，等待 GitHub Action 回调推送')
  } catch (e) {
    toast.error(e?.response?.data?.detail || '触发失败')
  } finally {
    zoomeyeFetching.value = false
  }
}

const daydaymapFetching = ref(false)
const daydaymapResult = ref(0)

const hunterFetching = ref(false)
const hunterResult = ref(0)

const handleHunterManualFetch = async () => {
  if (!settings.hunter.enabled) {
    toast.warning('请先启用 Hunter 数据源')
    return
  }
  hunterFetching.value = true
  try {
    const res = await request.post('/hunter/fetch')
    hunterResult.value = res.fetched
    toast.success(`拉取成功：获取到 ${res.fetched} 条数据`)
  } catch (e) {
    toast.error(e?.response?.data?.detail || '拉取失败')
  } finally {
    hunterFetching.value = false
  }
}

const handleDaydaymapManualFetch = async () => {
  if (!settings.daydaymap.enabled) {
    toast.warning('请先启用 DayDayMap 数据源')
    return
  }
  daydaymapFetching.value = true
  try {
    const res = await request.post('/daydaymap/fetch')
    daydaymapResult.value = res.fetched
    toast.success(`拉取成功：获取到 ${res.fetched} 条数据`)
  } catch (e) {
    toast.error(e?.response?.data?.detail || '拉取失败')
  } finally {
    daydaymapFetching.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const payload = {
      githubEnabled: settings.github.enabled,
      githubToken: settings.github.token,
      githubUserResultFetchCron: settings.github.userResultFetchCron,
      githubUserResultQuery: settings.github.userResultQuery,
      githubUserResultUrls: settings.github.userResultUrls,
      ozoneEnabled: settings.ozone.enabled,
      ozoneFetchCron: settings.ozone.fetchCron,
      zoomeyeEnabled: settings.zoomeye.enabled,
      zoomeyeFetchCron: settings.zoomeye.fetchCron,
      daydaymapEnabled: settings.daydaymap.enabled,
      daydaymapFetchCron: settings.daydaymap.fetchCron,
      hunterEnabled: settings.hunter.enabled,
      hunterApiKey: settings.hunter.apiKey,
      hunterFetchCron: settings.hunter.fetchCron,
      concurrency: settings.engine.concurrency,
      timeout: settings.engine.timeout,
      configDelay: settings.engine.configDelay,
      scanCron: settings.scheduling.scanCron,
      janitorCron: settings.scheduling.janitorCron,
      callbackToken: settings.security.callbackToken
    }
    await settingsStore.update(payload)
    toast.success('设置已保存')
  } catch (e) {
    console.error('保存失败:', e)
    toast.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
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
.settings-flow {
  width: 100%;
  max-width: var(--max-content);
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 90px;
}

@media (min-width: 768px) {
  .settings-flow { max-width: 720px; }
}
@media (min-width: 1024px) {
  .settings-flow { max-width: 1100px; }
}
@media (min-width: 1440px) {
  .settings-flow { max-width: 1400px; }
}

.settings-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.01);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--bg-neutral);
  padding-bottom: 10px;
}
.card-icon {
  font-size: 18px !important;
  color: var(--color-blue);
  font-variation-settings: 'FILL' 0, 'wght' 500;
}
.card-title-group h2 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

/* 启用开关 */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  margin-left: auto;
}
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 22px;
}
.slider:before {
  position: absolute;
  content: '';
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}
input:checked + .slider { background-color: var(--color-green); }
input:checked + .slider:before { transform: translateX(18px); }

.field-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.4;
  padding-left: 2px;
}

.textarea-input {
  font-family: var(--font-mono);
  font-size: 12px;
  resize: vertical;
  line-height: 1.6;
  padding: 8px 12px;
}

.save-btn {
  background: var(--color-blue);
  color: #FFFFFF;
  border: none;
  padding: 6px 12px;
  border-radius: var(--radius-btn);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}
.save-btn:active {
  transform: scale(0.96);
  background: #0066D6;
}
.save-btn-icon {
  font-size: 16px !important;
  font-variation-settings: 'FILL' 0, 'wght' 600, 'GRAD' 0, 'opsz' 24;
}

.fetch-btn {
  background: var(--bg-neutral);
  color: var(--color-blue);
  border: none;
  padding: 10px 16px;
  border-radius: var(--radius-input);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}
.fetch-btn:active {
  transform: scale(0.98);
  background: #E8E8ED;
}
.fetch-btn.fetching {
  opacity: 0.6;
  pointer-events: none;
}
.fetch-btn-mini {
  background: var(--color-blue);
  color: #fff;
  border: none;
  padding: 10px 16px;
  border-radius: var(--radius-input);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}
.fetch-btn-mini:active {
  transform: scale(0.96);
  background: #0066D6;
}
.fetch-btn-mini.fetching {
  opacity: 0.6;
  pointer-events: none;
}
.fetch-icon {
  font-size: 18px !important;
  font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
}
.spin {
  animation: spin 1s linear infinite;
}

.cron-help { margin-top: 4px; }
.cron-help summary {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-blue);
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.help-content {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--bg-neutral);
  border-radius: var(--radius-input);
}
.help-content p { margin: 4px 0; }
.help-content code {
  background: #E8E8ED;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
}
.help-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 6px 0;
}
.help-content td {
  padding: 3px 8px;
  border-bottom: 1px solid #E8E8ED;
}
.help-content td:first-child { font-weight: 600; color: var(--text-primary); }

/* 日志入口卡片 */
.logs-entry-card { cursor: pointer; transition: all 0.2s ease; }
.logs-entry-card:active { transform: scale(0.98); }
.entry-arrow {
  margin-left: auto;
  font-size: 22px !important;
  color: var(--text-muted);
}
</style>
