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
    if (payload.githubUserResultFetchCron !== undefined) data.value.github.userResultFetchCron = payload.githubUserResultFetchCron
    if (payload.githubUserResultQuery !== undefined) data.value.github.userResultQuery = payload.githubUserResultQuery
    if (payload.githubUserResultUrls !== undefined) data.value.github.userResultUrls = payload.githubUserResultUrls
    if (payload.ozoneEnabled !== undefined) data.value.ozone.enabled = payload.ozoneEnabled
    if (payload.ozoneFetchCron !== undefined) data.value.ozone.fetchCron = payload.ozoneFetchCron
    if (payload.zoomeyeEnabled !== undefined) data.value.zoomeye.enabled = payload.zoomeyeEnabled
    if (payload.zoomeyeFetchCron !== undefined) data.value.zoomeye.fetchCron = payload.zoomeyeFetchCron
    if (payload.daydaymapEnabled !== undefined) data.value.daydaymap.enabled = payload.daydaymapEnabled
    if (payload.daydaymapFetchCron !== undefined) data.value.daydaymap.fetchCron = payload.daydaymapFetchCron
    if (payload.hunterEnabled !== undefined) data.value.hunter.enabled = payload.hunterEnabled
    if (payload.hunterApiKey !== undefined) data.value.hunter.apiKey = payload.hunterApiKey
    if (payload.hunterFetchCron !== undefined) data.value.hunter.fetchCron = payload.hunterFetchCron
    if (payload.concurrency !== undefined) data.value.engine.concurrency = payload.concurrency
    if (payload.timeout !== undefined) data.value.engine.timeout = payload.timeout
    if (payload.configDelay !== undefined) data.value.engine.configDelay = payload.configDelay
    if (payload.scanCron !== undefined) data.value.scheduling.scanCron = payload.scanCron
    if (payload.janitorCron !== undefined) data.value.scheduling.janitorCron = payload.janitorCron
    if (payload.callbackToken !== undefined) {
      data.value.security.callbackToken = payload.callbackToken
    }
    return data.value
  }

  return { data, loaded, fetch, update }
})
