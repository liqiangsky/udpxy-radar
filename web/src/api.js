import axios from 'axios'
import { toast } from '@/components/Toast'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

// 请求拦截器：每次请求自动带上认证 token 和回调 token
request.interceptors.request.use((config) => {
  const authToken = localStorage.getItem('auth_token')
  if (authToken) {
    config.headers['X-Auth-Token'] = authToken
  }
  const callbackToken = localStorage.getItem('callback_token')
  if (callbackToken) {
    config.headers['X-Callback-Token'] = callbackToken
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    toast.error(msg)
    console.error('API 请求失败:', error)
    return Promise.reject(error)
  }
)

export default request
