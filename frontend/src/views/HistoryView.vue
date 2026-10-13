<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { explainError } from '../services/api'

const router = useRouter()
const attempts = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    attempts.value = (await api.get('/attempts/history')).data.attempts
  } catch (err) {
    error.value = explainError(err)
  } finally {
    loading.value = false
  }
})

function dateLabel(value) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}
</script>

<template>
  <section class="page-heading">
    <div><div class="eyebrow">YOUR PROGRESS</div><h1>Attempt history</h1><p class="muted">Every quiz is another step forward.</p></div>
    <button class="button button-quiet" @click="router.push('/')">← Dashboard</button>
  </section>
  <div v-if="error" class="alert alert-error">{{ error }}</div>
  <section class="panel">
    <div v-if="loading" class="empty-state">Loading your results…</div>
    <div v-else-if="!attempts.length" class="empty-state">Your quiz results will show up here after your first attempt.</div>
    <div v-else class="table-scroll">
      <table class="data-table">
        <thead><tr><th>Assessment</th><th>Date</th><th>Status</th><th>Score</th><th>Result</th><th></th></tr></thead>
        <tbody>
          <tr v-for="attempt in attempts" :key="attempt.id">
            <td><strong>{{ attempt.quiz_title }}</strong></td>
            <td>{{ dateLabel(attempt.start_time) }}</td>
            <td><span class="status-pill" :class="attempt.status === 'Submitted' ? 'status-done' : 'status-live'">{{ attempt.status === 'Submitted' ? 'Submitted' : 'In progress' }}</span></td>
            <td>{{ attempt.status === 'Submitted' ? `${attempt.total_score} / ${attempt.max_points}` : '—' }}</td>
            <td><span v-if="attempt.status === 'Submitted'" :class="attempt.score_percentage >= attempt.passing_score ? 'text-success' : 'text-muted'">{{ attempt.score_percentage }}%</span><span v-else>—</span></td>
            <td><RouterLink class="text-button" :to="{ name: 'attempt', params: { attemptId: attempt.id } }">{{ attempt.status === 'Submitted' ? 'Review' : 'Resume' }} →</RouterLink></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
