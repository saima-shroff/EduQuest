<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { explainError } from '../services/api'
import { login } from '../services/auth'

const router = useRouter()
const form = reactive({ name: '', email: '', password: '', role: 'Student' })
const error = ref('')
const success = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  success.value = ''
  loading.value = true
  try {
    await api.post('/auth/register', form)
    if (form.role === 'Instructor') {
      success.value = 'Your instructor account is registered and is waiting for admin approval. You can sign in after it is approved.'
    } else {
      await login({ email: form.email, password: form.password })
      router.push('/')
    }
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
      <p class="muted">Choose how you plan to use EduQuest.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">{{ success }} <RouterLink to="/login">Go to sign in</RouterLink></div>
      <label>Your name<input v-model.trim="form.name" autocomplete="name" maxlength="120" required /></label>
      <label>Email address<input v-model.trim="form.email" type="email" autocomplete="email" required /></label>
      <label>Password<input v-model="form.password" type="password" minlength="8" autocomplete="new-password" required /></label>
      <label>I'm joining as
        <select v-model="form.role">
          <option value="Student">Student</option>
          <option value="Instructor">Instructor (requires admin approval)</option>
        </select>
      </label>
      <button class="button button-primary button-full" :disabled="loading">{{ loading ? 'Creating account…' : 'Create account' }}</button>
      <p class="auth-switch">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
    </form>
  </section>
</template>
