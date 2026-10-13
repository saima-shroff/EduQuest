<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { explainError } from '../services/api'
import { login } from '../services/auth'

const router = useRouter()
const form = reactive({ name: '', email: '', password: '' })
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await api.post('/auth/register', form)
    await login({ email: form.email, password: form.password })
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
      <div class="eyebrow">A BETTER WAY TO PRACTICE</div>
      <h1>Small steps.<br /><span>Big progress.</span></h1>
      <p>Create your free student account and turn what you know into what you can do.</p>
      <div class="aside-stat"><strong>Practice</strong><span>with a little more purpose</span></div>
    </div>
    <form class="panel auth-card" @submit.prevent="submit">
      <div class="eyebrow">GET STARTED</div>
      <h2>Create your account</h2>
      <p class="muted">Student accounts can be created publicly. Instructor access is assigned by an administrator.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <label>Your name<input v-model.trim="form.name" autocomplete="name" maxlength="120" required /></label>
      <label>Email address<input v-model.trim="form.email" type="email" autocomplete="email" required /></label>
      <label>Password<input v-model="form.password" type="password" minlength="8" autocomplete="new-password" required /></label>
      <button class="button button-primary button-full" :disabled="loading">{{ loading ? 'Creating account…' : 'Create student account' }}</button>
      <p class="auth-switch">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
    </form>
  </section>
</template>
