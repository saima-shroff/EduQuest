import { createRouter, createWebHistory } from 'vue-router'
import { getUser, isAuthenticated } from '../services/auth'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DashboardView from '../views/DashboardView.vue'
import InstructorView from '../views/InstructorView.vue'
import QuizView from '../views/QuizView.vue'
import HistoryView from '../views/HistoryView.vue'
import AdminView from '../views/AdminView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView, meta: { auth: true } },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    { path: '/manage', name: 'manage', component: InstructorView, meta: { auth: true, role: 'Instructor' } },
    { path: '/attempts/:attemptId', name: 'attempt', component: QuizView, meta: { auth: true, role: 'Student' } },
    { path: '/history', name: 'history', component: HistoryView, meta: { auth: true, role: 'Student' } },
    { path: '/admin', name: 'admin', component: AdminView, meta: { auth: true, role: 'Admin' } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.auth && !isAuthenticated()) return { name: 'login' }
  if ((to.name === 'login' || to.name === 'register') && isAuthenticated()) return { name: 'dashboard' }
  if (to.name === 'dashboard' && getUser()?.roles?.includes('Admin')) return { name: 'admin' }
  if (to.meta.role && !getUser()?.roles?.includes(to.meta.role)) return { name: 'dashboard' }
})

export default router
