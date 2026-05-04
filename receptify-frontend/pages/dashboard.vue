<template>
  <div>
    <!-- Stat cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon stat-icon--blue">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-label">Total Calls</div>
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-sub">All time</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-icon--green">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-label">Calls Today</div>
          <div class="stat-value">{{ stats.today }}</div>
          <div class="stat-sub">Inbound</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-icon--violet">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-label">Active DIDs</div>
          <div class="stat-value">{{ stats.dids }}</div>
          <div class="stat-sub">Phone numbers</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-icon--amber">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-label">Plan</div>
          <div class="stat-value plan-value">
            <span class="badge badge-info" style="font-size:15px;padding:4px 12px">{{ authStore.tenant?.plan }}</span>
          </div>
          <div class="stat-sub">Current tier</div>
        </div>
      </div>
    </div>

    <!-- Recent calls table -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </svg>
          Recent Calls
        </h2>
        <NuxtLink to="/call-logs" class="btn btn-outline btn-sm">View all →</NuxtLink>
      </div>

      <p v-if="loading" class="empty-state">Loading…</p>
      <p v-else-if="!recentCalls.length" class="empty-state">No calls yet. Your receptionist is ready and waiting.</p>

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
            <td class="caller-cell">
              <div class="caller-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                </svg>
              </div>
              {{ call.caller_number }}
            </td>
            <td>
              <span :class="['badge', call.direction === 'inbound' ? 'badge-info' : 'badge-success']">
                {{ call.direction }}
              </span>
            </td>
            <td class="font-mono">{{ formatDuration(call.duration) }}</td>
            <td class="text-muted">{{ formatDate(call.started_at) }}</td>
          </tr>
        </tbody>
      </table>
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
/* ── Stat cards ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.15s, transform 0.15s;
}
.stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon svg { width: 22px; height: 22px; }
.stat-icon--blue   { background: #eff6ff; color: #2563eb; }
.stat-icon--green  { background: #f0fdf4; color: #16a34a; }
.stat-icon--violet { background: #f5f3ff; color: #7c3aed; }
.stat-icon--amber  { background: #fffbeb; color: #d97706; }

.stat-body { min-width: 0; }
.stat-label { font-size: 12px; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.stat-value { font-size: 28px; font-weight: 800; color: var(--color-text); letter-spacing: -0.03em; line-height: 1; margin-bottom: 4px; }
.plan-value { font-size: 16px; }
.stat-sub   { font-size: 12px; color: var(--color-text-muted); }

/* ── Table ── */
.caller-cell { display: flex; align-items: center; gap: 10px; font-weight: 500; }
.caller-icon {
  width: 30px;
  height: 30px;
  background: var(--color-primary-bg);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  flex-shrink: 0;
}
.caller-icon svg { width: 15px; height: 15px; }
.empty-state { padding: 32px 0; text-align: center; color: var(--color-text-muted); font-size: 14px; }
</style>
