<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { explainError } from '../services/api'

const route = useRoute()
const router = useRouter()
const attempt = ref(null)
const quiz = ref(null)
const answerMap = reactive({})
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const secondsLeft = ref(0)
let tickHandle
let saveHandle
let saveChain = Promise.resolve()

const complete = computed(() => attempt.value?.status === 'Submitted')
const timerLabel = computed(() => {
  const minutes = Math.floor(secondsLeft.value / 60)
  const seconds = secondsLeft.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})
const answerResults = computed(() => attempt.value?.answer_results || {})

async function loadAttempt() {
  error.value = ''
  try {
    const { data } = await api.get(`/attempts/${route.params.attemptId}`)
    attempt.value = data.attempt
    quiz.value = data.quiz
    Object.assign(answerMap, data.attempt.answers || {})
    updateClock()
  } catch (err) {
    error.value = explainError(err)
  } finally {
    loading.value = false
  }
}

function answersPayload() {
  return (quiz.value?.questions || []).map((question) => ({
    question_id: question.id,
    student_response: answerMap[question.id] || '',
  }))
}

function queueSave() {
  if (complete.value || !attempt.value || submitting.value) return
  clearTimeout(saveHandle)
  saveHandle = setTimeout(() => {
    saveChain = saveChain.then(() =>
      api.put(`/attempts/${attempt.value.id}/answers`, { answers: answersPayload() }),
    ).catch((err) => {
      error.value = explainError(err)
      if (err.response?.status === 409) loadAttempt()
    })
  }, 300)
}

function updateClock() {
  if (!attempt.value || complete.value) return
  secondsLeft.value = Math.max(0, Math.ceil((Date.parse(attempt.value.deadline) - Date.now()) / 1000))
  if (secondsLeft.value === 0) submitQuiz(true)
}

async function submitQuiz(expired = false) {
  if (!attempt.value || complete.value || submitting.value) return
  submitting.value = true
  clearTimeout(saveHandle)
  try {
    await saveChain
    const { data } = await api.post(`/attempts/${attempt.value.id}/submit`, {
      answers: answersPayload(),
    })
    attempt.value = data.attempt
    if (expired) error.value = ''
  } catch (err) {
    error.value = explainError(err)
    if (err.response?.status === 409) await loadAttempt()
  } finally {
    submitting.value = false
  }
}

function returnToDashboard() {
  router.push('/')
}

onMounted(async () => {
  await loadAttempt()
  tickHandle = setInterval(updateClock, 500)
})

onBeforeUnmount(() => {
  clearInterval(tickHandle)
  clearTimeout(saveHandle)
})
</script>

<template>
  <div v-if="loading" class="panel empty-state">Loading your assessment…</div>
  <div v-else-if="error && !quiz" class="panel empty-state"><div class="alert alert-error">{{ error }}</div><button class="button button-quiet" @click="returnToDashboard">Back to dashboard</button></div>
  <template v-else-if="quiz && attempt">
    <section class="page-heading assessment-heading">
      <div><div class="eyebrow">{{ complete ? 'ASSESSMENT RESULTS' : 'ASSESSMENT IN PROGRESS' }}</div><h1>{{ quiz.title }}</h1><p class="muted">{{ quiz.course_title }} <span>·</span> {{ quiz.chapter_title }}</p></div>
      <div v-if="!complete" class="timer-card" :class="{ 'timer-warning': secondsLeft < 60 }"><span>TIME REMAINING</span><strong>{{ timerLabel }}</strong></div>
      <div v-else class="score-card"><span>YOUR SCORE</span><strong>{{ attempt.total_score }} <small>/ {{ attempt.max_points }}</small></strong><em>{{ attempt.score_percentage }}%</em></div>
    </section>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="complete" class="result-banner" :class="{ 'result-pass': attempt.score_percentage >= quiz.passing_score }">
      <span class="result-symbol">{{ attempt.score_percentage >= quiz.passing_score ? '✓' : '↗' }}</span>
      <div><strong>{{ attempt.score_percentage >= quiz.passing_score ? 'Nice work — you passed!' : 'Keep practicing — you can do this.' }}</strong><p>Passing score: {{ quiz.passing_score }}%. Your attempt has been saved to your history.</p></div>
    </div>
    <section class="assessment-layout">
      <div class="question-stack">
        <article v-for="(question, index) in quiz.questions" :key="question.id" class="panel assessment-question">
          <div class="question-topline"><span>QUESTION {{ String(index + 1).padStart(2, '0') }}</span><span>{{ question.points }} {{ question.points === 1 ? 'point' : 'points' }}</span></div>
          <h2>{{ question.question_text }}</h2>
          <template v-if="question.question_type === 'Multiple-Choice'">
            <label v-for="option in question.options" :key="option.id" class="answer-option" :class="{ selected: String(answerMap[question.id] || '') === String(option.id), 'answer-right': complete && answerResults[question.id]?.is_correct && String(answerMap[question.id]) === String(option.id) }">
              <input v-model="answerMap[question.id]" type="radio" :name="`question-${question.id}`" :value="String(option.id)" :disabled="complete" @change="queueSave" />
              <span>{{ option.option_text }}</span>
              <span v-if="complete && String(answerMap[question.id]) === String(option.id)" class="answer-feedback">{{ answerResults[question.id]?.is_correct ? 'Correct' : 'Your answer' }}</span>
            </label>
          </template>
          <label v-else class="short-answer-label">Your answer
            <textarea v-model="answerMap[question.id]" rows="3" maxlength="10000" :disabled="complete" placeholder="Type your answer here…" @input="queueSave" />
          </label>
          <div v-if="complete" class="question-result" :class="answerResults[question.id]?.is_correct ? 'text-success' : 'text-muted'">
            {{ answerResults[question.id]?.is_correct ? `Correct · ${answerResults[question.id].points_earned} points` : 'Not quite · 0 points' }}
          </div>
        </article>
      </div>
      <aside class="panel assessment-aside">
        <div class="eyebrow">{{ complete ? 'ASSESSMENT COMPLETE' : 'BEFORE YOU SUBMIT' }}</div>
        <h3>{{ complete ? 'Progress made.' : 'You’ve got this.' }}</h3>
        <p class="muted">{{ complete ? 'Your responses are saved. Keep practicing to build confidence.' : 'Your answers save automatically. When time runs out, this assessment submits automatically.' }}</p>
        <div class="progress-line"><span>Questions</span><strong>{{ quiz.questions.length }}</strong></div>
        <div class="progress-line"><span>Total points</span><strong>{{ quiz.max_points }}</strong></div>
        <button v-if="!complete" class="button button-primary button-full" :disabled="submitting" @click="submitQuiz()">{{ submitting ? 'Submitting…' : 'Submit assessment' }}</button>
        <button v-else class="button button-primary button-full" @click="returnToDashboard">Back to dashboard</button>
        <p v-if="!complete" class="fine-print">Submitting is final. Make sure you’re happy with your answers.</p>
      </aside>
    </section>
  </template>
</template>
