<script setup>
import { onMounted, ref } from 'vue'
import api, { explainError } from '../services/api'

const dashboard = ref(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')
const approvingId = ref(null)

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    dashboard.value = (await api.get('/admin/dashboard')).data
  } catch (err) {
    error.value = explainError(err)
  } finally {
    loading.value = false
  }
}

async function approveInstructor(instructor) {
  approvingId.value = instructor.id
  error.value = ''
  notice.value = ''
  try {
    await api.post(`/admin/instructors/${instructor.id}/approve`)
    notice.value = `${instructor.name} is now an approved instructor.`
    await loadDashboard()
  } catch (err) {
    error.value = explainError(err)
  } finally {
    approvingId.value = null
  }
}

function dateLabel(value) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}

onMounted(loadDashboard)
</script>

<template>
  <section class="page-heading">
    <div>
      <div class="eyebrow">ADMINISTRATION</div>
      <h1>EduQuest overview.</h1>
      <p class="muted">Review instructor requests and keep an eye on learning activity.</p>
    </div>
    <button class="button button-quiet" :disabled="loading" @click="loadDashboard">Refresh data</button>
  </section>

  <div v-if="error" class="alert alert-error">{{ error }}</div>
  <div v-if="notice" class="alert alert-success">{{ notice }}</div>
  <div v-if="loading && !dashboard" class="panel empty-state">Loading the admin dashboard…</div>
  <template v-else-if="dashboard">
    <section class="stats-grid admin-stats">
      <div class="panel stat-card"><span>Registered students</span><strong>{{ dashboard.stats.students }}</strong><small>student accounts</small></div>
      <div class="panel stat-card"><span>Approved instructors</span><strong>{{ dashboard.stats.instructors }}</strong><small>can create courses and quizzes</small></div>
      <div class="panel stat-card"><span>Pending approval</span><strong>{{ dashboard.stats.pending_instructors }}</strong><small>instructor requests to review</small></div>
      <div class="panel stat-card"><span>Courses</span><strong>{{ dashboard.stats.courses }}</strong><small>created learning paths</small></div>
      <div class="panel stat-card"><span>Active quizzes</span><strong>{{ dashboard.stats.active_quizzes }}</strong><small>available assessments</small></div>
      <div class="panel stat-card"><span>Total attempts</span><strong>{{ dashboard.stats.total_attempts }}</strong><small>{{ dashboard.stats.in_progress_attempts }} in progress · {{ dashboard.stats.submitted_attempts }} submitted</small></div>
      <div class="panel stat-card"><span>Average submitted score</span><strong>{{ dashboard.stats.average_score_percentage }}%</strong><small>across graded attempts</small></div>
    </section>

    <section class="panel admin-section">
      <div class="section-title">
        <div><div class="eyebrow">REVIEW ACCESS</div><h2>Instructor approvals</h2></div>
        <span class="status-pill status-live">{{ dashboard.pending_instructors.length }} waiting</span>
      </div>
      <div v-if="!dashboard.pending_instructors.length" class="empty-state">No instructor requests need review right now.</div>
      <div v-else class="table-scroll">
        <table class="data-table">
          <thead><tr><th>Name</th><th>Email</th><th>Account</th><th></th></tr></thead>
          <tbody>
            <tr v-for="instructor in dashboard.pending_instructors" :key="instructor.id">
              <td><strong>{{ instructor.name }}</strong></td>
              <td>{{ instructor.email }}</td>
              <td><span class="status-pill status-live">Pending</span></td>
              <td><button class="button button-primary button-small" :disabled="approvingId === instructor.id" @click="approveInstructor(instructor)">{{ approvingId === instructor.id ? 'Approving…' : 'Approve instructor' }}</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel admin-section">
      <div class="section-title"><div><div class="eyebrow">CONTENT</div><h2>Recent quizzes</h2></div><span class="muted small">Showing up to 100</span></div>
      <div v-if="!dashboard.quizzes.length" class="empty-state">No quizzes have been created yet.</div>
      <div v-else class="table-scroll">
        <table class="data-table">
          <thead><tr><th>Quiz</th><th>Course / chapter</th><th>Created by</th><th>Questions</th><th>Attempts</th></tr></thead>
          <tbody>
            <tr v-for="quiz in dashboard.quizzes" :key="quiz.id">
              <td><strong>{{ quiz.title }}</strong></td>
              <td>{{ quiz.course_title }} / {{ quiz.chapter_title }}</td>
              <td>{{ quiz.instructor_name }}<small class="table-subtext">{{ quiz.instructor_email }}</small></td>
              <td>{{ quiz.question_count }}</td>
              <td>{{ quiz.attempt_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel admin-section">
      <div class="section-title"><div><div class="eyebrow">STUDENT ACTIVITY</div><h2>Recent attempts</h2></div><span class="muted small">Showing up to 100</span></div>
      <div v-if="!dashboard.recent_attempts.length" class="empty-state">Student quiz attempts will appear here.</div>
      <div v-else class="table-scroll">
        <table class="data-table">
          <thead><tr><th>Student</th><th>Quiz</th><th>Instructor</th><th>Started</th><th>Status</th><th>Score</th></tr></thead>
          <tbody>
            <tr v-for="attempt in dashboard.recent_attempts" :key="attempt.id">
              <td><strong>{{ attempt.student_name }}</strong><small class="table-subtext">{{ attempt.student_email }}</small></td>
              <td>{{ attempt.quiz_title }}</td>
              <td>{{ attempt.instructor_name }}</td>
              <td>{{ dateLabel(attempt.start_time) }}</td>
              <td><span class="status-pill" :class="attempt.status === 'Submitted' ? 'status-done' : 'status-live'">{{ attempt.status === 'Submitted' ? 'Submitted' : 'In progress' }}</span></td>
              <td>{{ attempt.status === 'Submitted' ? `${attempt.total_score} / ${attempt.max_points} (${attempt.score_percentage}%)` : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </template>
</template>
