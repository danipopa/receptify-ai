<template>
  <NuxtLayout name="auth">
    <h2 class="form-heading">Sign in to Receptify</h2>
    <form @submit.prevent="submit">
      <div class="form-group">
        <label class="form-label">Email</label>
        <input v-model="form.email" type="email" class="form-control" required autocomplete="email" />
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input v-model="form.password" type="password" class="form-control" required autocomplete="current-password" />
      </div>
      <p v-if="error" class="error-msg">{{ error }}</p>
      <button type="submit" class="btn btn-primary" style="width:100%" :disabled="loading">
        {{ loading ? "Signing in…" : "Sign in" }}
      </button>
    </form>
    <p class="form-footer">
      Don't have an account? <NuxtLink to="/register">Create one</NuxtLink>
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
.form-heading { font-size: 20px; font-weight: 600; margin-bottom: 24px; text-align: center; }
.error-msg { color: var(--color-danger); font-size: 13px; margin-bottom: 12px; }
.form-footer { margin-top: 20px; text-align: center; font-size: 13px; color: var(--color-text-muted); }
</style>
