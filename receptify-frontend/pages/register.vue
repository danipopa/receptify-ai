<template>
  <NuxtLayout name="auth">
    <h2 class="form-heading">Create your account</h2>
    <form @submit.prevent="submit">
      <div class="form-group">
        <label class="form-label">Business Name</label>
        <input v-model="form.name" type="text" class="form-control" required />
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
        <label class="form-label">Email</label>
        <input v-model="form.email" type="email" class="form-control" required />
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input v-model="form.password" type="password" class="form-control" required minlength="8" />
      </div>
      <p v-if="error" class="error-msg">{{ error }}</p>
      <button type="submit" class="btn btn-primary" style="width:100%" :disabled="loading">
        {{ loading ? "Creating account…" : "Create account" }}
      </button>
    </form>
    <p class="form-footer">
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
.form-heading { font-size: 20px; font-weight: 600; margin-bottom: 24px; text-align: center; }
.subdomain-input { display: flex; align-items: center; gap: 8px; }
.subdomain-input .form-control { flex: 1; }
.subdomain-suffix { font-size: 13px; color: var(--color-text-muted); white-space: nowrap; }
.error-msg { color: var(--color-danger); font-size: 13px; margin-bottom: 12px; }
.form-footer { margin-top: 20px; text-align: center; font-size: 13px; color: var(--color-text-muted); }
</style>
