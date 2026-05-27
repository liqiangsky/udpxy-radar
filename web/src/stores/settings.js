import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/api'

export const useSettingsStore = defineStore('settings', () => {
  const data = ref(null)
  const loaded = ref(false)

  const fetch = async (force = false) => {
    if (!force && loaded.value) return data.value
    const res = await request.get('/settings')
    data.value = res
    loaded.value = true
    // 同步 token 到 localStorage，供请求拦截器使用
    if (res?.security?.callbackToken) {
      localStorage.setItem('callback_token', res.security.callbackToken)
    }
    return res
  }

  const update = async (payload) => {
    // 先写入 localStorage，确保请求拦截器能拿到 token
    if (payload.callbackToken !== undefined) {
      localStorage.setItem('callback_token', payload.callbackToken)
    }
    await request.put('/settings', payload)
    if (!data.value) return data.value
    if (payload.githubEnabled !== undefined) data.value.github.enabled = payload.githubEnabled
    if (payload.githubToken !== undefined) data.value.github.token = payload.githubToken
    if (payload.githubScanCron !== undefined) data.value.github.scanCron = payload.githubScanCron
    if (payload.ozoneEnabled !== undefined) data.value.ozone.enabled = payload.ozoneEnabled
    if (payload.ozoneFetchCron !== undefined) data.value.ozone.fetchCron = payload.ozoneFetchCron
    if (payload.ozoneScanCron !== undefined) data.value.ozone.scanCron = payload.ozoneScanCron
    if (payload.zoomeyeEnabled !== undefined) data.value.zoomeye.enabled = payload.zoomeyeEnabled
    if (payload.zoomeyeFetchCron !== undefined) data.value.zoomeye.fetchCron = payload.zoomeyeFetchCron
    if (payload.zoomeyeScanCron !== undefined) data.value.zoomeye.scanCron = payload.zoomeyeScanCron
    if (payload.daydaymapEnabled !== undefined) data.value.daydaymap.enabled = payload.daydaymapEnabled
    if (payload.daydaymapFetchCron !== undefined) data.value.daydaymap.fetchCron = payload.daydaymapFetchCron
    if (payload.daydaymapScanCron !== undefined) data.value.daydaymap.scanCron = payload.daydaymapScanCron
    if (payload.hunterEnabled !== undefined) data.value.hunter.enabled = payload.hunterEnabled
    if (payload.hunterApiKey !== undefined) data.value.hunter.apiKey = payload.hunterApiKey
    if (payload.hunterFetchCron !== undefined) data.value.hunter.fetchCron = payload.hunterFetchCron
    if (payload.hunterScanCron !== undefined) data.value.hunter.scanCron = payload.hunterScanCron
    if (payload.concurrency !== undefined) data.value.engine.concurrency = payload.concurrency
    if (payload.timeout !== undefined) data.value.engine.timeout = payload.timeout
    if (payload.configDelay !== undefined) data.value.engine.configDelay = payload.configDelay
    if (payload.janitorCron !== undefined) data.value.scheduling.janitorCron = payload.janitorCron
    if (payload.callbackToken !== undefined) {
      data.value.security.callbackToken = payload.callbackToken
    }
    return data.value
  }

  return { data, loaded, fetch, update }
})
