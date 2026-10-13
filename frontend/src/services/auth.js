import { ref } from 'vue'
import api from './api'

const TOKEN_KEY = 'eduquest_token'
const USER_KEY = 'eduquest_user'

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const authUser = ref(readStoredUser())

export function getUser() {
  return authUser.value
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem(TOKEN_KEY))
}

export function hasRole(role) {
  return getUser()?.roles?.includes(role) || false
}

export async function login(credentials) {
  const { data } = await api.post('/auth/login', credentials)
  localStorage.setItem(TOKEN_KEY, data.auth_token)
  localStorage.setItem(USER_KEY, JSON.stringify(data.user))
  authUser.value = data.user
  return data.user
}

export async function register(details) {
  return (await api.post('/auth/register', details)).data.user
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  authUser.value = null
}
