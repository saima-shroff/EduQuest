<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { explainError } from '../services/api'
import { login } from '../services/auth'

const router = useRouter()
const form = reactive({ email: '', password: '' })
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await login(form)
    router.push('/')
  } catch (err) {
    error.value = explainError(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-layout">
    <div class="auth-aside">
      <div class="eyebrow">YOUR NEXT CHAPTER STARTS HERE</div>
      <h1>Make every<br /><span>answer count.</span></h1>
      <p>Learn, teach, and measure progress with assessments built for curious minds.</p>
      <div class="aside-stat"><strong>Learn</strong><span>at your own pace</span></div>
    </div>
    <form class="panel auth-card" @submit.prevent="submit">
      <div class="eyebrow">WELCOME BACK</div>
      <h2>Sign in to EduQuest</h2>
      <p class="muted">Pick up where you left off.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <label>Email address<input v-model.trim="form.email" type="email" autocomplete="email" required /></label>
      <label>Password<input v-model="form.password" type="password" autocomplete="current-password" required /></label>
      <button class="button button-primary button-full" :disabled="loading">{{ loading ? 'Signing in…' : 'Sign in' }}</button>
      <p class="auth-switch">New to EduQuest? <RouterLink to="/register">Create an account</RouterLink></p>
    </form>
  </section>
</template>
