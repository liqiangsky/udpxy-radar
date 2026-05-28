import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const isLoggedIn = ref(false)
  const username = ref('')

  // 从 localStorage 恢复登录状态（只存 token，session 在后端）
  const savedToken = localStorage.getItem('auth_token')
  const savedUser = localStorage.getItem('auth_username')
  if (savedToken) {
    isLoggedIn.value = true
    username.value = savedUser || ''
  }

  const login = async (user, pass) => {
    const res = await request.post('/login', { username: user, password: pass })
    isLoggedIn.value = true
    username.value = res.username
    localStorage.setItem('auth_token', res.token)
    localStorage.setItem('auth_username', res.username)
    return res
  }

  const logout = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      if (token) {
        await request.post('/logout?token=' + token)
      }
    } catch {
      // 静默
    }
    isLoggedIn.value = false
    username.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_username')
  }

  const getToken = () => localStorage.getItem('auth_token') || ''

  return { isLoggedIn, username, login, logout, getToken }
})
