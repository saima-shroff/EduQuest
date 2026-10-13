<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useRouter } from 'vue-router'
import api, { explainError } from '../services/api'
import { getUser } from '../services/auth'

const router = useRouter()
const user = computed(() => getUser())
const courses = ref([])
const quizzes = ref([])
const attempts = ref([])
const error = ref('')
const loading = ref(true)
const isInstructor = computed(() => user.value?.roles?.includes('Instructor'))
const activeByQuiz = computed(() => Object.fromEntries(
  attempts.value.filter((item) => item.status === 'InProgress').map((item) => [item.quiz_id, item]),
))

async function load() {
  error.value = ''
  loading.value = true
  try {
    const [courseResponse, quizResponse] = await Promise.all([
      api.get('/courses'),
      api.get('/quizzes'),
    ])
    courses.value = courseResponse.data.courses
    quizzes.value = quizResponse.data.quizzes
    if (!isInstructor.value) attempts.value = (await api.get('/attempts/history')).data.attempts
  } catch (err) {
    error.value = explainError(err)
  } finally {
    loading.value = false
  }
}

async function startQuiz(quiz) {
  error.value = ''
  try {
    const { data } = await api.post(`/quizzes/${quiz.id}/start`)
    router.push({ name: 'attempt', params: { attemptId: data.attempt.id } })
  } catch (err) {
    error.value = explainError(err)
  }
}

onMounted(load)
</script>

<template>
  <section class="page-heading">
    <div>
      <div class="eyebrow">{{ isInstructor ? 'INSTRUCTOR WORKSPACE' : 'STUDENT WORKSPACE' }}</div>
      <h1>Good to see you, {{ user?.name?.split(' ')[0] }}.</h1>
      <p class="muted">{{ isInstructor ? 'Build a learning path your students will remember.' : 'Choose a quiz and keep your learning momentum going.' }}</p>
    </div>
    <RouterLink v-if="isInstructor" class="button button-primary" to="/manage">＋ Manage courses</RouterLink>
    <RouterLink v-else class="button button-quiet" to="/history">View my results <span aria-hidden="true">↗</span></RouterLink>
  </section>

  <div v-if="error" class="alert alert-error">{{ error }}</div>
  <div v-if="loading" class="panel empty-state">Loading your workspace…</div>
  <template v-else>
    <section v-if="isInstructor" class="stats-grid">
      <div class="panel stat-card"><span>Courses</span><strong>{{ courses.length }}</strong><small>learning paths created</small></div>
      <div class="panel stat-card"><span>Quizzes</span><strong>{{ quizzes.length }}</strong><small>ready for learners</small></div>
      <div class="panel stat-card"><span>Role</span><strong>Instructor</strong><small>content creator access</small></div>
    </section>
    <section v-if="isInstructor" class="panel">
      <div class="section-title"><div><div class="eyebrow">YOUR LIBRARY</div><h2>Course overview</h2></div><RouterLink to="/manage">Edit content →</RouterLink></div>
      <div v-if="!courses.length" class="empty-state">No courses yet. Create your first course to get started.</div>
      <div v-else class="course-grid">
        <article v-for="course in courses" :key="course.id" class="course-card">
          <div class="course-icon">✦</div><div class="course-card-body">
            <h3>{{ course.title }}</h3><p>{{ course.description || 'No description yet.' }}</p>
            <div class="card-meta">{{ course.chapter_count }} {{ course.chapter_count === 1 ? 'chapter' : 'chapters' }}</div>
          </div>
        </article>
      </div>
    </section>
    <template v-else>
      <section class="stats-grid">
        <div class="panel stat-card"><span>Available quizzes</span><strong>{{ quizzes.length }}</strong><small>across your courses</small></div>
        <div class="panel stat-card"><span>Completed</span><strong>{{ attempts.filter(a => a.status === 'Submitted').length }}</strong><small>attempts in your history</small></div>
        <div class="panel stat-card"><span>In progress</span><strong>{{ attempts.filter(a => a.status === 'InProgress').length }}</strong><small>pick up where you left off</small></div>
      </section>
      <section class="panel">
        <div class="section-title"><div><div class="eyebrow">YOUR NEXT CHALLENGE</div><h2>Available quizzes</h2></div></div>
        <div v-if="!quizzes.length" class="empty-state">There are no published quizzes yet. Check back soon.</div>
        <div v-else class="quiz-list">
          <article v-for="quiz in quizzes" :key="quiz.id" class="quiz-row">
            <div class="quiz-icon">Q</div><div class="quiz-info">
              <h3>{{ quiz.title }}</h3><p>{{ quiz.course_title }} <span>·</span> {{ quiz.chapter_title }}</p>
              <div class="card-meta">{{ quiz.questions.length }} questions <span>·</span> {{ quiz.time_limit_minutes }} min <span>·</span> {{ quiz.max_points }} pts</div>
            </div>
            <button v-if="activeByQuiz[quiz.id]" class="button button-quiet" @click="router.push({ name: 'attempt', params: { attemptId: activeByQuiz[quiz.id].id } })">Resume</button>
            <button v-else class="button button-primary" @click="startQuiz(quiz)">Start quiz</button>
          </article>
        </div>
      </section>
    </template>
  </template>
</template>
