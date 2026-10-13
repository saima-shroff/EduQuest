import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('eduquest_token')
  if (token) config.headers['Authentication-Token'] = token
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('eduquest_token')
      localStorage.removeItem('eduquest_user')
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export function explainError(error) {
  return error.response?.data?.error || error.response?.data?.message || error.message || 'Something went wrong.'
}

export default api
