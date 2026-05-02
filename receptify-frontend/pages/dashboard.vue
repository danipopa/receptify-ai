<template>
  <div>
    <h1 class="page-title">Dashboard</h1>

    <div class="stats-grid">
      <div class="card stat-card">
        <div class="stat-label">Total Calls</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">Inbound Today</div>
        <div class="stat-value">{{ stats.today }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">Active DIDs</div>
        <div class="stat-value">{{ stats.dids }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">Plan</div>
        <div class="stat-value plan-badge">
          <span class="badge badge-info">{{ authStore.tenant?.plan }}</span>
        </div>
      </div>
    </div>

    <div class="card recent-calls">
      <h2 class="section-title">Recent Calls</h2>
      <p v-if="loading" class="muted">Loading…</p>
      <p v-else-if="!recentCalls.length" class="muted">No calls yet.</p>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Caller</th>
            <th>Direction</th>
            <th>Duration</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="call in recentCalls" :key="call.id">
            <td>{{ call.caller_number }}</td>
            <td><span :class="['badge', call.direction === 'inbound' ? 'badge-info' : 'badge-success']">{{ call.direction }}</span></td>
            <td>{{ formatDuration(call.duration) }}</td>
            <td>{{ formatDate(call.started_at) }}</td>
          </tr>
        </tbody>
      </table>
      <NuxtLink to="/call-logs" class="view-all">View all call logs →</NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const authStore = useAuthStore()

const loading = ref(true)
const recentCalls = ref<any[]>([])
const stats = reactive({ total: 0, today: 0, dids: 0 })

onMounted(async () => {
  try {
    const [logsRes, didsRes] = await Promise.all([
      api.get<{ call_logs: any[]; meta: any }>("/call_logs?page=1"),
      api.get<{ dids: any[]; meta: any }>("/dids"),
    ])
    recentCalls.value = logsRes.call_logs.slice(0, 5)
    stats.total = logsRes.meta.total
    stats.dids  = didsRes.meta.total
    const today = new Date().toDateString()
    stats.today = logsRes.call_logs.filter(
      (c) => new Date(c.started_at).toDateString() === today
    ).length
  } finally {
    loading.value = false
  }
})

function formatDuration(s: number) {
  if (!s) return "—"
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, "0")}`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}
</script>

<style scoped>
.page-title { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { text-align: center; padding: 20px; }
.stat-label { font-size: 13px; color: var(--color-text-muted); margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--color-primary); }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--color-border); font-size: 13px; }
.table th { font-weight: 600; color: var(--color-text-muted); }
.muted { color: var(--color-text-muted); font-size: 14px; }
.view-all { display: inline-block; margin-top: 16px; font-size: 13px; }
</style>
