<template>
  <div>
    <NuxtLink to="/call-logs" class="back-link">← Back to Call Logs</NuxtLink>

    <div v-if="loading" class="muted">Loading…</div>
    <template v-else-if="log">
      <h1 class="page-title">Call from {{ log.caller_number }}</h1>

      <div class="meta-grid">
        <div class="card meta-card">
          <div class="meta-label">Direction</div>
          <span :class="['badge', log.direction === 'inbound' ? 'badge-info' : 'badge-success']">{{ log.direction }}</span>
        </div>
        <div class="card meta-card">
          <div class="meta-label">Duration</div>
          <div class="meta-value">{{ formatDuration(log.duration) }}</div>
        </div>
        <div class="card meta-card">
          <div class="meta-label">Started At</div>
          <div class="meta-value">{{ new Date(log.started_at).toLocaleString() }}</div>
        </div>
        <div class="card meta-card">
          <div class="meta-label">DID</div>
          <div class="meta-value">{{ log.did?.number ?? "—" }}</div>
        </div>
      </div>

      <div v-if="log.summary" class="card section-card">
        <h2 class="section-title">Summary</h2>
        <p class="section-body">{{ log.summary }}</p>
      </div>

      <div v-if="log.transcript" class="card section-card">
        <h2 class="section-title">Transcript</h2>
        <pre class="transcript">{{ log.transcript }}</pre>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const api = useApi()

const loading = ref(true)
const log = ref<any>(null)

onMounted(async () => {
  try {
    log.value = await api.get<any>(`/call_logs/${route.params.id}`)
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
</script>

<style scoped>
.back-link { font-size: 13px; display: inline-block; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
.meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 20px; }
.meta-card { padding: 16px; }
.meta-label { font-size: 12px; color: var(--color-text-muted); margin-bottom: 6px; font-weight: 600; text-transform: uppercase; }
.meta-value { font-size: 15px; font-weight: 600; }
.section-card { margin-bottom: 16px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.section-body { font-size: 14px; line-height: 1.6; }
.transcript { font-size: 13px; line-height: 1.7; white-space: pre-wrap; font-family: "Cascadia Code", monospace; }
.muted { color: var(--color-text-muted); }
</style>
