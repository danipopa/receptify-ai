<template>
  <div v-if="workspace">
    <div class="page-header">
      <div>
        <NuxtLink to="/clients">← All client workspaces</NuxtLink>
        <h1 class="page-title">{{ workspace.name }}</h1>
        <p class="text-muted">Client-specific settings are isolated from your other workspaces.</p>
      </div>
      <span :class="['badge', workspace.knowledge_status === 'ready' ? 'badge-success' : 'badge-warning']">
        Voice knowledge: {{ workspace.knowledge_status }}
      </span>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="notice" class="alert alert-success">{{ notice }}</div>

    <section class="card section-card">
      <h2 class="section-title">Client settings</h2>
      <form class="form-grid" @submit.prevent="saveSettings">
        <div class="form-group">
          <label class="form-label">Name</label>
          <input v-model="settings.name" class="form-control" required />
        </div>
        <div class="form-group">
          <label class="form-label">Website</label>
          <input v-model="settings.website_url" class="form-control" type="url" />
        </div>
        <div class="form-group">
          <label class="form-label">Default language</label>
          <select v-model="settings.locale" class="form-control">
            <option value="en-GB">British English</option>
            <option value="en-US">American English</option>
            <option value="fr-FR">French</option>
            <option value="it-IT">Italian</option>
            <option value="es-ES">Spanish</option>
            <option value="ro-RO">Romanian</option>
          </select>
          <span class="form-hint">This stores the workspace locale; the deployed STT/TTS models are still English-only.</span>
        </div>
        <div class="form-group">
          <label class="form-label">Time zone</label>
          <select v-model="settings.timezone" class="form-control" required>
            <option v-for="timeZone in timeZones" :key="timeZone" :value="timeZone">{{ timeZone }}</option>
          </select>
          <span class="form-hint">Weekly hours, closures and spoken slot times use this time zone.</span>
        </div>
        <div class="form-actions"><button class="btn btn-primary" :disabled="saving">Save settings</button></div>
      </form>
    </section>

    <section class="card section-card">
      <div class="section-heading">
        <div>
          <h2 class="section-title">Phone number requests</h2>
          <p class="text-muted">Dial a simulator number from a Linphone account registered to this FreeSWITCH. It routes to this workspace only; it is not reachable from the public phone network.</p>
        </div>
      </div>
      <form class="inline-form" @submit.prevent="requestNumber">
        <div class="form-group compact">
          <label class="form-label">Country / language</label>
          <select v-model="countryCode" class="form-control">
            <option value="GB">United Kingdom — British English</option>
            <option value="US">United States — American English</option>
            <option value="FR">France — French</option>
            <option value="IT">Italy — Italian</option>
            <option value="ES">Spain — Spanish</option>
            <option value="RO">Romania — Romanian</option>
          </select>
        </div>
        <button class="btn btn-primary" :disabled="saving">{{ saving ? "Requesting…" : "Request mock number" }}</button>
      </form>
      <div v-if="workspace.number_requests.length" class="table-wrap">
        <table class="table">
          <thead><tr><th>Number</th><th>Country</th><th>Language</th><th>Type</th><th>Requested</th></tr></thead>
          <tbody>
            <tr v-for="item in workspace.number_requests" :key="item.id">
              <td class="font-mono">{{ item.number }}</td><td>{{ item.country_name }}</td><td>{{ item.locale }}</td>
              <td><span class="badge badge-warning">Simulator only</span></td>
              <td>{{ new Date(item.created_at).toLocaleDateString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card section-card">
      <div class="section-heading">
        <div>
          <h2 class="section-title">RAG knowledge draft</h2>
          <p class="text-muted">Review and edit the source notes. Drafts are not used by the phone agent until published.</p>
        </div>
        <span :class="['badge', workspace.knowledge_status === 'ready' ? 'badge-success' : 'badge-warning']">
          {{ workspace.knowledge_status }}
        </span>
      </div>
      <div class="form-group">
        <label class="form-label">Source URL or note</label>
        <input v-model="knowledgeSource" class="form-control" />
      </div>
      <div class="form-group">
        <label class="form-label">Knowledge content</label>
        <textarea v-model="knowledgeContent" class="form-control knowledge-editor" rows="12" />
      </div>
      <div class="form-actions">
        <button class="btn btn-outline" :disabled="saving" @click="saveKnowledge('draft')">Save as draft</button>
        <button class="btn btn-primary" :disabled="saving" @click="saveKnowledge('ready')">Publish to phone agent</button>
      </div>
    </section>

    <section class="card section-card">
      <div class="section-heading">
        <div>
          <h2 class="section-title">Appointment types</h2>
          <p class="text-muted">The starter workspaces include an editable 30-minute placeholder.</p>
        </div>
      </div>
      <form class="inline-form" @submit.prevent="addAppointmentType">
        <div class="form-group compact">
          <label class="form-label">Type name</label>
          <input v-model="typeForm.name" class="form-control" required placeholder="General consultation" />
        </div>
        <div class="form-group duration-field">
          <label class="form-label">Duration (minutes)</label>
          <input v-model.number="typeForm.duration_minutes" class="form-control" type="number" min="1" max="480" required />
        </div>
        <button class="btn btn-primary" :disabled="saving">Add type</button>
      </form>
      <div v-if="!workspace.appointment_types.length" class="empty-state">Add an appointment type before configuring availability.</div>
      <div v-for="item in workspace.appointment_types" :key="item.id" class="editable-row">
        <input v-model="item.name" class="form-control" aria-label="Appointment type name" />
        <input v-model.number="item.duration_minutes" class="form-control duration-field" type="number" min="1" max="480" aria-label="Duration in minutes" />
        <label class="toggle"><input v-model="item.active" type="checkbox" /> Active</label>
        <button class="btn btn-outline btn-sm" :disabled="saving" @click="updateAppointmentType(item)">Save</button>
        <button class="btn btn-danger btn-sm" :disabled="saving" @click="deleteAppointmentType(item.id)">Remove</button>
      </div>
    </section>

    <section class="card section-card">
      <h2 class="section-title">Weekly availability</h2>
      <p class="text-muted">Add one or more working-hour ranges for each weekday. Appointment duration determines slot length.</p>
      <form class="inline-form schedule-form" @submit.prevent="addRule">
        <div class="form-group compact">
          <label class="form-label">Day</label>
          <select v-model.number="ruleForm.day_of_week" class="form-control">
            <option v-for="(day, index) in days" :key="day" :value="index">{{ day }}</option>
          </select>
        </div>
        <div class="form-group compact">
          <label class="form-label">From</label>
          <input v-model="ruleForm.start_time" class="form-control" type="time" required />
        </div>
        <div class="form-group compact">
          <label class="form-label">To</label>
          <input v-model="ruleForm.end_time" class="form-control" type="time" required />
        </div>
        <button class="btn btn-primary" :disabled="saving">Add hours</button>
      </form>
      <p v-if="!workspace.availability_rules.length" class="empty-state">No weekly hours yet. Voice booking remains unavailable until hours are added.</p>
      <div v-for="rule in workspace.availability_rules" :key="rule.id" class="list-row">
        <span><strong>{{ days[rule.day_of_week] }}</strong> {{ rule.start_time }}–{{ rule.end_time }}</span>
        <button class="btn btn-danger btn-sm" :disabled="saving" @click="deleteRule(rule.id)">Remove</button>
      </div>
    </section>

    <section class="card section-card">
      <h2 class="section-title">Date-specific closures and blocks</h2>
      <form class="inline-form schedule-form" @submit.prevent="addException">
        <div class="form-group compact">
          <label class="form-label">Date</label>
          <input v-model="exceptionForm.date" class="form-control" type="date" required />
        </div>
        <div class="form-group compact">
          <label class="form-label">Block type</label>
          <select v-model="exceptionForm.all_day" class="form-control">
            <option :value="true">Closed all day</option>
            <option :value="false">Block specific hours</option>
          </select>
        </div>
        <template v-if="!exceptionForm.all_day">
          <div class="form-group compact"><label class="form-label">From</label><input v-model="exceptionForm.start_time" class="form-control" type="time" required /></div>
          <div class="form-group compact"><label class="form-label">To</label><input v-model="exceptionForm.end_time" class="form-control" type="time" required /></div>
        </template>
        <div class="form-group compact">
          <label class="form-label">Description</label>
          <input v-model="exceptionForm.description" class="form-control" placeholder="Holiday or unavailable" />
        </div>
        <button class="btn btn-primary" :disabled="saving">Add block</button>
      </form>
      <p v-if="!workspace.availability_exceptions.length" class="empty-state">No date-specific blocks.</p>
      <div v-for="item in workspace.availability_exceptions" :key="item.id" class="list-row">
        <span><strong>{{ item.date }}</strong> — {{ item.all_day ? "Closed all day" : `${item.start_time}–${item.end_time}` }} <span class="text-muted">{{ item.description }}</span></span>
        <button class="btn btn-danger btn-sm" :disabled="saving" @click="deleteException(item.id)">Remove</button>
      </div>
    </section>

    <section class="card section-card">
      <h2 class="section-title">Appointments</h2>
      <p v-if="!workspace.appointments?.length" class="empty-state">No appointments booked yet.</p>
      <div v-for="appointment in workspace.appointments || []" :key="appointment.id" class="list-row appointment-row">
        <span>
          <strong>{{ appointment.appointment_type_name }}</strong>
          — {{ formatDate(appointment.starts_at) }}
          with {{ appointment.caller_name }} ({{ appointment.callback_number }})
          <span v-if="appointment.purpose" class="text-muted">Reason: {{ appointment.purpose }}</span>
          <span :class="['badge', appointment.status === 'confirmed' ? 'badge-success' : 'badge-neutral']">{{ appointment.status }}</span>
        </span>
        <button v-if="appointment.status === 'confirmed'" class="btn btn-outline btn-sm" :disabled="saving" @click="cancelAppointment(appointment.id)">Cancel</button>
      </div>
    </section>
  </div>
  <p v-else-if="loading" class="empty-state">Loading workspace…</p>
  <div v-else class="alert alert-error">{{ error || "Client workspace not found." }}</div>
</template>

<script setup lang="ts">
const api = useApi()
const route = useRoute()
const workspace = ref<any>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref("")
const notice = ref("")
const countryCode = ref("GB")
const knowledgeContent = ref("")
const knowledgeSource = ref("")
const settings = reactive({ name: "", website_url: "", timezone: "UTC", locale: "en-GB" })
const typeForm = reactive({ name: "", duration_minutes: 30 })
const ruleForm = reactive({ day_of_week: 1, start_time: "09:00", end_time: "17:00" })
const exceptionForm = reactive({ date: "", all_day: true, start_time: "09:00", end_time: "17:00", description: "" })
const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
const workspaceId = String(route.params.id)
const timeZones = computed(() => useTimeZones(settings.timezone))

onMounted(loadWorkspace)

async function loadWorkspace() {
  loading.value = true
  error.value = ""
  try {
    const result = await api.get<{ client_workspace: any }>(`/client_workspaces/${workspaceId}`)
    workspace.value = result.client_workspace
    knowledgeContent.value = workspace.value.knowledge_content || ""
    knowledgeSource.value = workspace.value.knowledge_source || ""
    Object.assign(settings, {
      name: workspace.value.name,
      website_url: workspace.value.website_url || "",
      timezone: workspace.value.timezone,
      locale: workspace.value.locale,
    })
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Could not load the client workspace."
  } finally {
    loading.value = false
  }
}

async function perform(action: () => Promise<unknown>, message: string) {
  saving.value = true
  error.value = ""
  notice.value = ""
  try {
    await action()
    await loadWorkspace()
    notice.value = message
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "The request could not be completed."
  } finally {
    saving.value = false
  }
}

function saveSettings() {
  return perform(() => api.patch(`/client_workspaces/${workspaceId}`, settings), "Client settings saved.")
}

function saveKnowledge(status: "draft" | "ready") {
  return perform(
    () => api.patch(`/client_workspaces/${workspaceId}/knowledge`, {
      knowledge_content: knowledgeContent.value,
      knowledge_source: knowledgeSource.value,
      knowledge_status: status,
    }),
    status === "ready" ? "Knowledge published to the phone agent." : "Knowledge saved as a draft."
  )
}

function requestNumber() {
  return perform(
    () => api.post(`/client_workspaces/${workspaceId}/number_requests`, { country_code: countryCode.value }),
    "Simulator number requested. Dial it through a Linphone account registered to FreeSWITCH."
  )
}

function addAppointmentType() {
  return perform(async () => {
    await api.post(`/client_workspaces/${workspaceId}/appointment_types`, typeForm)
    Object.assign(typeForm, { name: "", duration_minutes: 30 })
  }, "Appointment type added.")
}

function updateAppointmentType(item: any) {
  return perform(
    () => api.patch(`/client_workspaces/${workspaceId}/appointment_types/${item.id}`, {
      name: item.name,
      duration_minutes: item.duration_minutes,
      active: item.active,
    }),
    "Appointment type saved."
  )
}

function deleteAppointmentType(id: number) {
  if (!confirm("Remove this appointment type? Types with existing appointments cannot be removed.")) return
  return perform(() => api.delete(`/client_workspaces/${workspaceId}/appointment_types/${id}`), "Appointment type removed.")
}

function addRule() {
  return perform(
    () => api.post(`/client_workspaces/${workspaceId}/availability_rules`, ruleForm),
    "Weekly availability added."
  )
}

function deleteRule(id: number) {
  return perform(() => api.delete(`/client_workspaces/${workspaceId}/availability_rules/${id}`), "Weekly hours removed.")
}

function addException() {
  return perform(
    () => api.post(`/client_workspaces/${workspaceId}/availability_exceptions`, exceptionForm),
    "Date-specific block added."
  )
}

function deleteException(id: number) {
  return perform(() => api.delete(`/client_workspaces/${workspaceId}/availability_exceptions/${id}`), "Date block removed.")
}

function cancelAppointment(id: number) {
  if (!confirm("Cancel this appointment?")) return
  return perform(() => api.delete(`/client_workspaces/${workspaceId}/appointments/${id}`), "Appointment cancelled.")
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: workspace.value?.timezone || "UTC",
  }).format(new Date(value))
}
</script>

<style scoped>
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; margin: 6px 0 4px; }
.section-card { margin-bottom: 18px; }
.section-title { font-size: 17px; font-weight: 700; margin-bottom: 12px; }
.section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.section-heading .section-title { margin-bottom: 4px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; }
.inline-form { display: flex; align-items: flex-end; gap: 12px; margin: 16px 0; }
.compact { flex: 1; margin-bottom: 0; }
.duration-field { max-width: 170px; }
.table-wrap { overflow-x: auto; margin-top: 14px; }
.knowledge-editor { min-height: 220px; font-family: ui-monospace, monospace; }
.editable-row, .list-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-top: 1px solid var(--color-border); }
.editable-row .form-control:first-child { flex: 1; }
.list-row { justify-content: space-between; }
.toggle { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.empty-state { padding: 14px 0; color: var(--color-text-muted); }
.appointment-row span:first-child { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
@media (max-width: 760px) {
  .page-header { align-items: flex-start; flex-direction: column; }
  .form-grid { grid-template-columns: 1fr; }
  .inline-form, .editable-row { align-items: stretch; flex-direction: column; }
  .duration-field { max-width: none; }
  .list-row { align-items: flex-start; }
}
</style>
