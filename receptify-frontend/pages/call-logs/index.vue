<template>
  <div>
    <h1 class="page-title">Call Logs</h1>

    <div class="card">
      <div class="filters">
        <select v-model="direction" class="form-control" style="width:160px" @change="fetch">
          <option value="">All directions</option>
          <option value="inbound">Inbound</option>
          <option value="outbound">Outbound</option>
        </select>
      </div>

      <p v-if="loading" class="muted">Loading…</p>
      <p v-else-if="!logs.length" class="muted">No call logs found.</p>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Caller</th>
            <th>Direction</th>
            <th>Duration</th>
            <th>Started At</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td>{{ log.caller_number }}</td>
            <td><span :class="['badge', log.direction === 'inbound' ? 'badge-info' : 'badge-success']">{{ log.direction }}</span></td>
            <td>{{ formatDuration(log.duration) }}</td>
            <td>{{ new Date(log.started_at).toLocaleString() }}</td>
            <td><NuxtLink :to="`/call-logs/${log.id}`" class="view-link">View →</NuxtLink></td>
          </tr>
        </tbody>
      </table>

      <div v-if="meta.total > meta.limit" class="pagination">
        <button class="btn btn-outline" :disabled="page <= 1" @click="changePage(page - 1)">← Prev</button>
        <span class="page-info">Page {{ page }} of {{ totalPages }}</span>
        <button class="btn btn-outline" :disabled="page >= totalPages" @click="changePage(page + 1)">Next →</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()

const loading   = ref(true)
const logs      = ref<any[]>([])
const direction = ref("")
const page      = ref(1)
const meta      = reactive({ total: 0, limit: 25 })

const totalPages = computed(() => Math.ceil(meta.total / meta.limit) || 1)

onMounted(fetch)

async function fetch() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value) })
    if (direction.value) params.set("direction", direction.value)
    const res = await api.get<{ call_logs: any[]; meta: any }>(`/call_logs?${params}`)
    logs.value     = res.call_logs
    meta.total     = res.meta.total
    meta.limit     = res.meta.limit
  } finally {
    loading.value = false
  }
}

function changePage(p: number) {
  page.value = p
  fetch()
}

function formatDuration(s: number) {
  if (!s) return "—"
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, "0")}`
}
</script>

<style scoped>
.page-title { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
.filters { margin-bottom: 16px; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--color-border); font-size: 13px; }
.table th { font-weight: 600; color: var(--color-text-muted); }
.muted { color: var(--color-text-muted); }
.view-link { font-size: 13px; }
.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.page-info { font-size: 13px; color: var(--color-text-muted); }
</style>
