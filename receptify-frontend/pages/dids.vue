<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Phone Numbers (DIDs)</h1>
      <button class="btn btn-primary" @click="openAdd">+ Add DID</button>
    </div>

    <div class="card">
      <p v-if="loading" class="muted">Loading…</p>
      <p v-else-if="!dids.length" class="muted">No phone numbers configured yet.</p>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Number</th>
            <th>Provider</th>
            <th>Gateway</th>
            <th>Status</th>
            <th>Added</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="did in dids" :key="did.id">
            <td>{{ did.number }}</td>
            <td>{{ did.provider }}</td>
            <td>
              <span :class="['badge', gatewayBadgeClass(did.gateway_type)]">{{ did.gateway_type || 'none' }}</span>
            </td>
            <td><span :class="['badge', did.status === 'active' ? 'badge-success' : 'badge-warning']">{{ did.status }}</span></td>
            <td>{{ new Date(did.created_at).toLocaleDateString() }}</td>
            <td class="actions">
              <button class="btn btn-outline" style="padding:4px 10px;font-size:12px" @click="openEdit(did)">Edit</button>
              <button class="btn btn-danger" style="padding:4px 10px;font-size:12px" @click="remove(did.id)">Remove</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add / Edit DID modal -->
    <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
      <div class="card modal-card">
        <h2 class="section-title">{{ editing ? 'Edit Phone Number' : 'Add Phone Number' }}</h2>
        <form @submit.prevent="editing ? updateDid() : addDid()">

          <!-- Basic fields -->
          <div class="form-group">
            <label class="form-label">Phone Number (E.164)</label>
            <input v-model="form.number" class="form-control" placeholder="+15551234567" :disabled="!!editing" required />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Provider</label>
              <select v-model="form.provider" class="form-control">
                <option>twilio</option>
                <option>vonage</option>
                <option>signalwire</option>
                <option>bandwidth</option>
                <option>custom</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Status</label>
              <select v-model="form.status" class="form-control">
                <option>active</option>
                <option>inactive</option>
              </select>
            </div>
          </div>

          <!-- Gateway section -->
          <div class="section-divider">SIP Gateway</div>
          <div class="form-group">
            <label class="form-label">Gateway Type</label>
            <select v-model="form.gateway_type" class="form-control">
              <option value="none">None (manage externally)</option>
              <option value="sip_trunk">SIP Trunk (IP auth)</option>
              <option value="sip_registration">SIP Registration (user/pass)</option>
            </select>
          </div>

          <template v-if="form.gateway_type !== 'none'">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">SIP Host</label>
                <input v-model="form.gateway_host" class="form-control" placeholder="sip.provider.com" :required="form.gateway_type !== 'none'" />
              </div>
              <div class="form-group" style="max-width:100px">
                <label class="form-label">Port</label>
                <input v-model.number="form.gateway_port" class="form-control" type="number" placeholder="5060" />
              </div>
            </div>

            <template v-if="form.gateway_type === 'sip_registration'">
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Username</label>
                  <input v-model="form.gateway_user" class="form-control" placeholder="username" required />
                </div>
                <div class="form-group">
                  <label class="form-label">Password</label>
                  <input v-model="form.gateway_password" class="form-control" type="password" placeholder="••••••••" :required="!editing" />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">Realm <span class="muted">(optional)</span></label>
                <input v-model="form.gateway_realm" class="form-control" placeholder="sip.provider.com" />
              </div>
            </template>
          </template>

          <p v-if="formError" class="error-msg">{{ formError }}</p>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="closeModal">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="formLoading">
              {{ formLoading ? (editing ? 'Saving…' : 'Adding…') : (editing ? 'Save' : 'Add') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()

const loading     = ref(true)
const dids        = ref<any[]>([])
const showModal   = ref(false)
const editing     = ref<any>(null)
const formError   = ref("")
const formLoading = ref(false)

const defaultForm = () => ({
  number: "", provider: "twilio", status: "active",
  gateway_type: "none", gateway_host: "", gateway_port: 5060,
  gateway_user: "", gateway_password: "", gateway_realm: "",
})
const form = reactive(defaultForm())

onMounted(fetchDids)

async function fetchDids() {
  loading.value = true
  try {
    const res = await api.get<{ dids: any[] }>("/dids")
    dids.value = res.dids
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = null
  Object.assign(form, defaultForm())
  showModal.value = true
}

function openEdit(did: any) {
  editing.value = did
  Object.assign(form, {
    number:           did.number,
    provider:         did.provider,
    status:           did.status,
    gateway_type:     did.gateway_type || "none",
    gateway_host:     did.gateway_host || "",
    gateway_port:     did.gateway_port || 5060,
    gateway_user:     did.gateway_user || "",
    gateway_password: "",  // never pre-fill password
    gateway_realm:    did.gateway_realm || "",
  })
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editing.value = null
  formError.value = ""
}

function buildPayload() {
  const p: any = {
    provider: form.provider,
    status: form.status,
    gateway_type: form.gateway_type,
    gateway_host: form.gateway_host || null,
    gateway_port: form.gateway_port || 5060,
    gateway_user: form.gateway_user || null,
    gateway_realm: form.gateway_realm || null,
  }
  if (form.gateway_password) p.gateway_password = form.gateway_password
  return p
}

async function addDid() {
  formError.value = ""
  formLoading.value = true
  try {
    const did = await api.post<any>("/dids", { ...buildPayload(), number: form.number })
    dids.value.unshift(did)
    closeModal()
  } catch (e: any) {
    formError.value = e.message
  } finally {
    formLoading.value = false
  }
}

async function updateDid() {
  formError.value = ""
  formLoading.value = true
  try {
    const did = await api.patch<any>(`/dids/${editing.value.id}`, buildPayload())
    const idx = dids.value.findIndex(d => d.id === editing.value.id)
    if (idx !== -1) dids.value[idx] = did
    closeModal()
  } catch (e: any) {
    formError.value = e.message
  } finally {
    formLoading.value = false
  }
}

async function remove(id: number) {
  if (!confirm("Remove this phone number?")) return
  await api.delete(`/dids/${id}`)
  dids.value = dids.value.filter((d) => d.id !== id)
}

function gatewayBadgeClass(type: string) {
  if (type === "sip_registration") return "badge-primary"
  if (type === "sip_trunk")        return "badge-info"
  return "badge-neutral"
}
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title  { font-size: 20px; font-weight: 600; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--color-border); font-size: 13px; }
.table th { font-weight: 600; color: var(--color-text-muted); }
.actions { display: flex; gap: 6px; }
.muted { color: var(--color-text-muted); font-weight: 400; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-card { width: 100%; max-width: 520px; padding: 28px; max-height: 90vh; overflow-y: auto; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.section-divider { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--color-text-muted); border-top: 1px solid var(--color-border); padding-top: 14px; margin: 16px 0 12px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
.error-msg { color: var(--color-danger); font-size: 13px; margin-bottom: 12px; }
.badge-primary { background: #3b82f620; color: #3b82f6; }
.badge-info    { background: #06b6d420; color: #0891b2; }
.badge-neutral { background: var(--color-surface-2, #f1f5f9); color: var(--color-text-muted); }
</style>

