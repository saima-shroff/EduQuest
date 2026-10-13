<script setup>
import { useRoute, useRouter } from 'vue-router'
import { authUser, isAuthenticated, logout } from './services/auth'

const route = useRoute()
const router = useRouter()
const user = authUser

function signOut() {
  logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">E</span>
        <span>EduQuest</span>
      </RouterLink>
      <nav v-if="user" class="nav-links">
        <RouterLink to="/">Dashboard</RouterLink>
        <RouterLink v-if="user?.roles?.includes('Instructor')" to="/manage">Manage content</RouterLink>
        <RouterLink v-if="user?.roles?.includes('Student')" to="/history">My results</RouterLink>
      </nav>
      <div v-if="user" class="user-menu">
        <span class="user-greeting">{{ user?.name }}</span>
        <button class="button button-quiet button-small" @click="signOut">Sign out</button>
      </div>
      <div v-else class="nav-links">
        <RouterLink :class="{ active: route.name === 'login' }" to="/login">Sign in</RouterLink>
        <RouterLink class="button button-small" to="/register">Create account</RouterLink>
      </div>
    </header>
    <main class="page">
      <RouterView />
    </main>
    <footer class="footer">EduQuest <span>·</span> Practice with purpose</footer>
  </div>
</template>
