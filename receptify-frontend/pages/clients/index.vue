<template>
  <div>
    <div class="page-header">
      <div>
        <h1 class="page-title">Client workspaces</h1>
        <p class="text-muted">Manage each client’s phone setup, knowledge and appointments separately.</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-outline" :disabled="loading" @click="seedStarters">Add starter clients</button>
        <button class="btn btn-primary" @click="showCreate = true">+ Add client</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <p v-if="loading" class="empty-state">Loading client workspaces…</p>
    <div v-else-if="!workspaces.length" class="card empty-card">
      <h2 class="section-title">No client workspaces yet</h2>
      <p class="text-muted">Create one, or add the two starter clients and editable draft content.</p>
      <button class="btn btn-primary" :disabled="saving" @click="seedStarters">Add Mobiletel and inregistrare-marca.com</button>
    </div>
    <div v-else class="workspace-grid">
      <article v-for="workspace in workspaces" :key="workspace.id" class="card workspace-card">
        <div class="workspace-card-head">
          <div>
            <h2 class="section-title">{{ workspace.name }}</h2>
            <a v-if="workspace.website_url" :href="workspace.website_url" target="_blank" rel="noreferrer">
              {{ workspace.website_url }}
            </a>
          </div>
          <span :class="['badge', workspace.knowledge_status === 'ready' ? 'badge-success' : 'badge-warning']">
            RAG {{ workspace.knowledge_status }}
          </span>
        </div>
        <div class="workspace-meta">
          <span>{{ workspace.locale }}</span>
          <span>{{ workspace.timezone }}</span>
          <span>{{ workspace.number_requests.length }} simulator number(s)</span>
          <span>{{ workspace.appointment_types.length }} appointment type(s)</span>
        </div>
        <NuxtLink :to="`/clients/${workspace.id}`" class="btn btn-outline">Manage workspace</NuxtLink>
      </article>
    </div>

    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="card modal-card">
        <h2 class="section-title">Create a client workspace</h2>
        <form @submit.prevent="createWorkspace">
          <div class="form-group">
            <label class="form-label">Client name</label>
            <input v-model="form.name" class="form-control" required maxlength="120" />
          </div>
          <div class="form-group">
            <label class="form-label">Website</label>
            <input v-model="form.website_url" class="form-control" type="url" placeholder="https://example.com" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Default language</label>
              <select v-model="form.locale" class="form-control">
                <option value="en-GB">British English</option>
                <option value="en-US">American English</option>
                <option value="fr-FR">French</option>
                <option value="it-IT">Italian</option>
                <option value="es-ES">Spanish</option>
                <option value="ro-RO">Romanian</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Time zone</label>
              <select v-model="form.timezone" class="form-control" required>
                <option v-for="timeZone in timeZones" :key="timeZone" :value="timeZone">{{ timeZone }}</option>
              </select>
            </div>
          </div>
          <p v-if="formError" class="error-msg">{{ formError }}</p>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showCreate = false">Cancel</button>
            <button class="btn btn-primary" :disabled="saving">{{ saving ? "Creating…" : "Create workspace" }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface ClientWorkspace {
  id: number
  name: string
  website_url: string | null
  timezone: string
  locale: string
  knowledge_status: "draft" | "ready"
  appointment_types: Array<{ id: number }>
  number_requests: Array<{ id: number }>
}

const api = useApi()
const workspaces = ref<ClientWorkspace[]>([])
const loading = ref(true)
const saving = ref(false)
const showCreate = ref(false)
const error = ref("")
const formError = ref("")
const form = reactive({ name: "", website_url: "", timezone: "UTC", locale: "en-GB" })
const timeZones = useTimeZones(form.timezone)

onMounted(loadWorkspaces)

async function loadWorkspaces() {
  loading.value = true
  error.value = ""
  try {
    const result = await api.get<{ client_workspaces: ClientWorkspace[] }>("/client_workspaces")
    workspaces.value = result.client_workspaces
    if (workspaces.value.length === 0) {
      await seedStarters()
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Could not load client workspaces."
  } finally {
    loading.value = false
  }
}

async function seedStarters() {
  saving.value = true
  error.value = ""
  try {
    const result = await api.post<{ client_workspaces: ClientWorkspace[] }>("/client_workspaces/seed_starters", {})
    workspaces.value = result.client_workspaces
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Could not create starter workspaces."
  } finally {
    saving.value = false
  }
}

async function createWorkspace() {
  saving.value = true
  formError.value = ""
  try {
    await api.post("/client_workspaces", form)
    showCreate.value = false
    Object.assign(form, { name: "", website_url: "", timezone: "UTC", locale: "en-GB" })
    await loadWorkspaces()
  } catch (cause) {
    formError.value = cause instanceof Error ? cause.message : "Could not create the workspace."
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.header-actions { display: flex; gap: 8px; }
.workspace-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.workspace-card { display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.workspace-card-head { width: 100%; display: flex; justify-content: space-between; gap: 12px; }
.section-title { font-size: 17px; font-weight: 700; margin-bottom: 6px; }
.workspace-meta { display: flex; flex-wrap: wrap; gap: 8px 14px; color: var(--color-text-muted); font-size: 13px; }
.empty-card { display: flex; flex-direction: column; align-items: flex-start; gap: 14px; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal-card { width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
.error-msg { color: var(--color-danger); font-size: 13px; margin-bottom: 12px; }
@media (max-width: 700px) { .page-header { align-items: flex-start; flex-direction: column; } .header-actions { width: 100%; } }
</style>
