<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Phone Numbers (DIDs)</h1>
      <button class="btn btn-primary" @click="showAdd = true">+ Add DID</button>
    </div>

    <div class="card">
      <p v-if="loading" class="muted">Loading…</p>
      <p v-else-if="!dids.length" class="muted">No phone numbers configured yet.</p>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Number</th>
            <th>Provider</th>
            <th>Status</th>
            <th>Added</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="did in dids" :key="did.id">
            <td>{{ did.number }}</td>
            <td>{{ did.provider }}</td>
            <td><span :class="['badge', did.status === 'active' ? 'badge-success' : 'badge-warning']">{{ did.status }}</span></td>
            <td>{{ new Date(did.created_at).toLocaleDateString() }}</td>
            <td>
              <button class="btn btn-danger" style="padding:4px 10px;font-size:12px" @click="remove(did.id)">Remove</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add DID modal -->
    <div v-if="showAdd" class="modal-backdrop" @click.self="showAdd = false">
      <div class="card modal-card">
        <h2 class="section-title">Add Phone Number</h2>
        <form @submit.prevent="addDid">
          <div class="form-group">
            <label class="form-label">Phone Number (E.164)</label>
            <input v-model="newDid.number" class="form-control" placeholder="+15551234567" required />
          </div>
          <div class="form-group">
            <label class="form-label">Provider</label>
            <select v-model="newDid.provider" class="form-control">
              <option>twilio</option>
              <option>vonage</option>
              <option>signalwire</option>
              <option>bandwidth</option>
            </select>
          </div>
          <p v-if="addError" class="error-msg">{{ addError }}</p>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showAdd = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="addLoading">
              {{ addLoading ? "Adding…" : "Add" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()

const loading  = ref(true)
const dids     = ref<any[]>([])
const showAdd  = ref(false)
const addError = ref("")
const addLoading = ref(false)
const newDid   = reactive({ number: "", provider: "twilio" })

onMounted(async () => {
  await fetchDids()
})

async function fetchDids() {
  loading.value = true
  try {
    const res = await api.get<{ dids: any[] }>("/dids")
    dids.value = res.dids
  } finally {
    loading.value = false
  }
}

async function addDid() {
  addError.value = ""
  addLoading.value = true
  try {
    const did = await api.post<any>("/dids", newDid)
    dids.value.unshift(did)
    showAdd.value = false
    newDid.number = ""
  } catch (e: any) {
    addError.value = e.message
  } finally {
    addLoading.value = false
  }
}

async function remove(id: number) {
  if (!confirm("Remove this phone number?")) return
  await api.delete(`/dids/${id}`)
  dids.value = dids.value.filter((d) => d.id !== id)
}
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title  { font-size: 20px; font-weight: 600; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--color-border); font-size: 13px; }
.table th { font-weight: 600; color: var(--color-text-muted); }
.muted { color: var(--color-text-muted); }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-card { width: 100%; max-width: 420px; padding: 28px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
.error-msg { color: var(--color-danger); font-size: 13px; margin-bottom: 12px; }
</style>
