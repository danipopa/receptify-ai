<template>
  <NuxtLayout name="auth">
    <div class="auth-header">
      <h2 class="auth-title">Create your account</h2>
      <p class="auth-subtitle">Start with a free plan — no credit card required</p>
    </div>
    <form @submit.prevent="submit">
      <div class="form-group">
        <label class="form-label">Business Name</label>
        <input v-model="form.name" type="text" class="form-control" required placeholder="Acme Corp" />
      </div>
      <div class="form-group">
        <label class="form-label">Subdomain</label>
        <div class="subdomain-input">
          <input v-model="form.subdomain" type="text" class="form-control" placeholder="your-business"
            pattern="[a-z0-9\-]+" title="Lowercase letters, numbers, and hyphens only" required />
          <span class="subdomain-suffix">.receptify.us</span>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Email Address</label>
        <input v-model="form.email" type="email" class="form-control" required placeholder="you@company.com" />
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input v-model="form.password" type="password" class="form-control" required minlength="8" placeholder="Minimum 8 characters" />
      </div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
        {{ loading ? "Creating account…" : "Create account" }}
      </button>
    </form>
    <p class="auth-footer">
      Already have an account? <NuxtLink to="/login">Sign in</NuxtLink>
    </p>
  </NuxtLayout>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const api = useApi()
const authStore = useAuthStore()
const form = reactive({ name: "", subdomain: "", email: "", password: "" })
const error = ref("")
const loading = ref(false)

async function submit() {
  error.value = ""
  loading.value = true
  try {
    const data = await api.post<{ token: string; tenant: any }>("/auth/register", form)
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
.subdomain-input { display: flex; align-items: center; gap: 8px; }
.subdomain-input .form-control { flex: 1; }
.subdomain-suffix { font-size: 13px; color: var(--color-text-muted); white-space: nowrap; font-weight: 500; }
.auth-footer { margin-top: 20px; text-align: center; font-size: 13px; color: var(--color-text-muted); }
</style>
