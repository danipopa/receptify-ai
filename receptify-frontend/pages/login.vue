<template>
  <NuxtLayout name="auth">
    <div class="auth-header">
      <h2 class="auth-title">Welcome back</h2>
      <p class="auth-subtitle">Sign in to your Receptify account</p>
    </div>
    <form @submit.prevent="submit">
      <div class="form-group">
        <label class="form-label">Email address</label>
        <input v-model="form.email" type="email" class="form-control" required autocomplete="email" placeholder="you@company.com" />
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input v-model="form.password" type="password" class="form-control" required autocomplete="current-password" placeholder="••••••••" />
      </div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
        {{ loading ? "Signing in…" : "Sign in" }}
      </button>
    </form>
    <p class="auth-footer">
      Don't have an account? <NuxtLink to="/register">Create one free</NuxtLink>
    </p>
  </NuxtLayout>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const api = useApi()
const authStore = useAuthStore()
const form = reactive({ email: "", password: "" })
const error = ref("")
const loading = ref(false)

async function submit() {
  error.value = ""
  loading.value = true
  try {
    const data = await api.post<{ token: string; tenant: any }>("/auth/login", form)
    authStore.setAuth(data.token, data.tenant)
    await navigateTo("/dashboard")
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-header { margin-bottom: 28px; }
.auth-title  { font-size: 22px; font-weight: 700; color: var(--color-text); letter-spacing: -0.02em; margin-bottom: 4px; }
.auth-subtitle { font-size: 14px; color: var(--color-text-muted); }
.auth-footer { margin-top: 20px; text-align: center; font-size: 13px; color: var(--color-text-muted); }
</style>
