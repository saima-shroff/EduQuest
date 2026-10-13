<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api, { explainError } from '../services/api'

const courses = ref([])
const quizzes = ref([])
const loading = ref(true)
const error = ref('')
const notice = ref('')
const courseForm = reactive({ id: null, title: '', description: '' })
const chapterForm = reactive({ course_id: '', title: '', sequence_order: '' })
const quizForm = reactive({
  id: null, chapter_id: '', title: '', time_limit_minutes: 30, passing_score: 60,
  questions: [],
})
const chapters = computed(() => courses.value.flatMap((course) =>
  (course.chapters || []).map((chapter) => ({ ...chapter, course_title: course.title })),
))

function questionTemplate() {
  return {
    question_text: '', question_type: 'Multiple-Choice', points: 1,
    options: [
      { option_text: '', is_correct: true },
      { option_text: '', is_correct: false },
    ],
    accepted_answers: [''],
  }
}

async function load() {
  error.value = ''
  loading.value = true
  try {
    const [courseResponse, quizResponse] = await Promise.all([
      api.get('/courses'), api.get('/quizzes'),
    ])
    courses.value = courseResponse.data.courses.map((course) => ({ ...course, chapters: [] }))
    await Promise.all(courses.value.map(async (course) => {
      course.chapters = (await api.get(`/courses/${course.id}`)).data.course.chapters
    }))
    quizzes.value = quizResponse.data.quizzes
  } catch (err) {
    error.value = explainError(err)
  } finally {
    loading.value = false
  }
}

function editCourse(course) {
  courseForm.id = course.id
  courseForm.title = course.title
  courseForm.description = course.description
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function resetCourse() {
  courseForm.id = null
  courseForm.title = ''
  courseForm.description = ''
}

async function saveCourse() {
  error.value = ''
  notice.value = ''
  try {
    const body = { title: courseForm.title, description: courseForm.description }
    if (courseForm.id) await api.put(`/courses/${courseForm.id}`, body)
    else await api.post('/courses', body)
    notice.value = courseForm.id ? 'Course updated.' : 'Course created.'
    resetCourse()
    await load()
  } catch (err) {
    error.value = explainError(err)
  }
}

async function deleteCourse(course) {
  if (!window.confirm(`Delete “${course.title}”? Courses with quiz attempts cannot be deleted.`)) return
  try {
    await api.delete(`/courses/${course.id}`)
    notice.value = 'Course deleted.'
    await load()
  } catch (err) {
    error.value = explainError(err)
  }
}

async function addChapter() {
  error.value = ''
  try {
    await api.post(`/courses/${chapterForm.course_id}/chapters`, {
      title: chapterForm.title,
      ...(chapterForm.sequence_order ? { sequence_order: Number(chapterForm.sequence_order) } : {}),
    })
    chapterForm.title = ''
    chapterForm.sequence_order = ''
    notice.value = 'Chapter added.'
    await load()
  } catch (err) {
    error.value = explainError(err)
  }
}

function beginQuiz(quiz = null) {
  quizForm.id = quiz?.id ?? null
  quizForm.chapter_id = quiz?.chapter_id ?? (chapters.value[0]?.id || '')
  quizForm.title = quiz?.title ?? ''
  quizForm.time_limit_minutes = quiz?.time_limit_minutes ?? 30
  quizForm.passing_score = quiz?.passing_score ?? 60
  quizForm.questions = quiz
    ? quiz.questions.map((question) => ({
      question_text: question.question_text,
      question_type: question.question_type,
      points: question.points,
      options: question.options.map((option) => ({
        option_text: option.option_text, is_correct: option.is_correct,
      })),
      accepted_answers: [...(question.accepted_answers || [''])],
    }))
    : [questionTemplate()]
  document.getElementById('quiz-editor')?.scrollIntoView({ behavior: 'smooth' })
}

function resetQuiz() {
  beginQuiz()
  quizForm.id = null
  quizForm.title = ''
}

function addQuestion() {
  quizForm.questions.push(questionTemplate())
}

function addOption(question) {
  question.options.push({ option_text: '', is_correct: false })
}

function removeOption(question, index) {
  if (question.options.length > 2) question.options.splice(index, 1)
}

function setCorrectOption(question, selectedIndex) {
  question.options.forEach((option, index) => {
    option.is_correct = index === selectedIndex
  })
}

async function saveQuiz() {
  error.value = ''
  notice.value = ''
  const body = {
    chapter_id: Number(quizForm.chapter_id),
    title: quizForm.title,
    time_limit_minutes: Number(quizForm.time_limit_minutes),
    passing_score: Number(quizForm.passing_score),
    questions: quizForm.questions.map((question) => ({
      ...question,
      points: Number(question.points),
      options: question.options.map((option) => ({ ...option })),
      accepted_answers: question.accepted_answers.filter((answer) => answer.trim()),
    })),
  }
  try {
    if (quizForm.id) {
      const { chapter_id: _chapterId, ...update } = body
      await api.put(`/quizzes/${quizForm.id}`, update)
      notice.value = 'Quiz updated.'
    } else {
      await api.post('/quizzes', body)
      notice.value = 'Quiz created.'
    }
    resetQuiz()
    await load()
  } catch (err) {
    error.value = explainError(err)
  }
}

async function deleteQuiz(quiz) {
  if (!window.confirm(`Delete “${quiz.title}”?`)) return
  try {
    await api.delete(`/quizzes/${quiz.id}`)
    notice.value = 'Quiz deleted.'
    await load()
  } catch (err) {
    error.value = explainError(err)
  }
}

onMounted(load)
</script>

<template>
  <section class="page-heading">
    <div><div class="eyebrow">INSTRUCTOR STUDIO</div><h1>Build your learning path.</h1><p class="muted">Organize content into courses, chapters, and quizzes.</p></div>
  </section>
  <div v-if="error" class="alert alert-error">{{ error }}</div>
  <div v-if="notice" class="alert alert-success">{{ notice }}</div>
  <div v-if="loading" class="panel empty-state">Loading your content…</div>
  <template v-else>
    <section class="management-grid">
      <form class="panel form-panel" @submit.prevent="saveCourse">
        <div class="eyebrow">COURSE</div><h2>{{ courseForm.id ? 'Edit course' : 'Create a course' }}</h2>
        <label>Course title<input v-model.trim="courseForm.title" maxlength="160" required /></label>
        <label>Description<textarea v-model="courseForm.description" rows="3" /></label>
        <div class="form-actions"><button class="button button-primary">{{ courseForm.id ? 'Save changes' : 'Create course' }}</button><button v-if="courseForm.id" type="button" class="button button-quiet" @click="resetCourse">Cancel</button></div>
      </form>
      <form class="panel form-panel" @submit.prevent="addChapter">
        <div class="eyebrow">CHAPTER</div><h2>Add a chapter</h2>
        <label>Course<select v-model="chapterForm.course_id" required><option value="" disabled>Select a course</option><option v-for="course in courses" :key="course.id" :value="course.id">{{ course.title }}</option></select></label>
        <label>Chapter title<input v-model.trim="chapterForm.title" maxlength="160" required /></label>
        <label>Sequence order <span class="optional">(optional)</span><input v-model="chapterForm.sequence_order" type="number" min="1" placeholder="Next in sequence" /></label>
        <div class="form-actions"><button class="button button-primary" :disabled="!courses.length">Add chapter</button></div>
      </form>
    </section>

    <section class="panel management-section">
      <div class="section-title"><div><div class="eyebrow">STRUCTURE</div><h2>Your courses</h2></div></div>
      <div v-if="!courses.length" class="empty-state">Create a course above to start organizing content.</div>
      <article v-for="course in courses" :key="course.id" class="manage-course">
        <div class="manage-course-heading"><div><h3>{{ course.title }}</h3><p>{{ course.description || 'No description' }}</p></div><div class="form-actions"><button class="text-button" @click="editCourse(course)">Edit</button><button class="text-button danger-text" @click="deleteCourse(course)">Delete</button></div></div>
        <div v-if="!course.chapters.length" class="muted small">No chapters yet.</div>
        <div v-for="chapter in course.chapters" :key="chapter.id" class="chapter-line">
          <span class="chapter-number">{{ chapter.sequence_order }}</span>
          <div><strong>{{ chapter.title }}</strong><small>{{ chapter.quizzes.length }} quizzes</small></div>
          <span v-if="chapter.quizzes.length" class="chapter-quiz-names">{{ chapter.quizzes.map(q => q.title).join(' · ') }}</span>
        </div>
      </article>
    </section>

    <section id="quiz-editor" class="panel management-section">
      <div class="section-title"><div><div class="eyebrow">ASSESSMENT</div><h2>{{ quizForm.id ? 'Edit quiz' : 'Create a quiz' }}</h2></div></div>
      <div v-if="!chapters.length" class="empty-state">Add a course and chapter before creating a quiz.</div>
      <form v-else class="quiz-editor-form" @submit.prevent="saveQuiz">
        <div class="form-grid">
          <label>Quiz title<input v-model.trim="quizForm.title" maxlength="160" required /></label>
          <label>Chapter<select v-model="quizForm.chapter_id" :disabled="Boolean(quizForm.id)" required><option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">{{ chapter.course_title }} / {{ chapter.title }}</option></select></label>
          <label>Time limit (minutes)<input v-model.number="quizForm.time_limit_minutes" type="number" min="1" max="1440" required /></label>
          <label>Passing score (%)<input v-model.number="quizForm.passing_score" type="number" min="0" max="100" required /></label>
        </div>
        <article v-for="(question, index) in quizForm.questions" :key="index" class="question-editor">
          <div class="question-editor-heading"><h3>Question {{ index + 1 }}</h3><button v-if="quizForm.questions.length > 1" type="button" class="text-button danger-text" @click="quizForm.questions.splice(index, 1)">Remove</button></div>
          <div class="form-grid question-meta">
            <label>Question text<textarea v-model.trim="question.question_text" rows="2" required /></label>
            <label>Type<select v-model="question.question_type"><option>Multiple-Choice</option><option>Short-Answer</option></select></label>
            <label>Points<input v-model.number="question.points" type="number" min="0.01" step="0.25" required /></label>
          </div>
          <div v-if="question.question_type === 'Multiple-Choice'" class="options-editor">
            <div v-for="(option, optionIndex) in question.options" :key="optionIndex" class="option-editor">
              <input v-model.trim="option.option_text" :aria-label="`Option ${optionIndex + 1}`" placeholder="Answer option" required />
              <label class="correct-choice"><input type="radio" :name="`correct-${index}`" :checked="option.is_correct" @change="setCorrectOption(question, optionIndex)" /> Correct</label>
              <button v-if="question.options.length > 2" type="button" class="text-button danger-text" @click="removeOption(question, optionIndex)">Remove</button>
            </div>
            <button type="button" class="text-button" @click="addOption(question)">＋ Add option</button>
          </div>
          <div v-else class="accepted-editor">
            <label>Accepted answer(s) <span class="optional">Comparison ignores case and extra whitespace</span></label>
            <div v-for="(answer, answerIndex) in question.accepted_answers" :key="answerIndex" class="option-editor">
              <input v-model.trim="question.accepted_answers[answerIndex]" placeholder="Accepted answer" required />
              <button v-if="question.accepted_answers.length > 1" type="button" class="text-button danger-text" @click="question.accepted_answers.splice(answerIndex, 1)">Remove</button>
            </div>
            <button type="button" class="text-button" @click="question.accepted_answers.push('')">＋ Add accepted answer</button>
          </div>
        </article>
        <div class="form-actions editor-actions"><button type="button" class="button button-quiet" @click="addQuestion">＋ Add question</button><span class="spacer" /><button v-if="quizForm.id" type="button" class="button button-quiet" @click="resetQuiz">Cancel</button><button class="button button-primary">{{ quizForm.id ? 'Save quiz' : 'Create quiz' }}</button></div>
      </form>
    </section>

    <section class="panel management-section">
      <div class="section-title"><div><div class="eyebrow">PUBLISHED</div><h2>Your quizzes</h2></div></div>
      <div v-if="!quizzes.length" class="empty-state">Quizzes you create will appear here.</div>
      <article v-for="quiz in quizzes" :key="quiz.id" class="quiz-row">
        <div class="quiz-icon">Q</div><div class="quiz-info"><h3>{{ quiz.title }}</h3><p>{{ quiz.course_title }} <span>·</span> {{ quiz.chapter_title }}</p><div class="card-meta">{{ quiz.questions.length }} questions · {{ quiz.time_limit_minutes }} min</div></div>
        <div class="form-actions"><button class="button button-quiet button-small" @click="beginQuiz(quiz)">Edit</button><button class="button button-quiet button-small danger-text" @click="deleteQuiz(quiz)">Delete</button></div>
      </article>
    </section>
  </template>
</template>
