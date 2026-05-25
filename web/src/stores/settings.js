import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/api'

export const useSettingsStore = defineStore('settings', () => {
  const data = ref(null)
  const loaded = ref(false)

  const fetch = async () => {
    if (loaded.value) return data.value
    const res = await request.get('/settings')
    data.value = res
    loaded.value = true
    return res
  }

  const update = async (payload) => {
    await request.put('/settings', payload)
    data.value = { ...data.value, ...payload }
    return data.value
  }

  return { data, loaded, fetch, update }
})
