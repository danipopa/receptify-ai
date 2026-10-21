<template>
  <div class="admin-page">
    <div class="page-heading">
      <div>
        <h2 class="section-title">Business Overview</h2>
        <p class="text-muted">Customers, phone numbers, subscriptions, and recent business activity.</p>
      </div>
      <button class="btn btn-outline btn-sm" :disabled="loading" @click="loadOverview">
        {{ loading ? "Refreshing…" : "Refresh" }}
      </button>
    </div>

    <p v-if="loading && !overview" class="empty-state">Loading platform data…</p>
    <div v-else-if="error" class="alert alert-error">{{ error }}</div>

    <template v-else-if="overview">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-body">
            <div class="stat-label">Customers</div>
            <div class="stat-value">{{ overview.metrics.customer_count }}</div>
            <div class="stat-sub">{{ overview.metrics.active_customer_count }} active</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-body">
            <div class="stat-label">Paid Plans</div>
            <div class="stat-value">{{ overview.metrics.paid_customer_count }}</div>
            <div class="stat-sub">Customer subscriptions</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-body">
            <div class="stat-label">Phone Numbers</div>
            <div class="stat-value">{{ overview.metrics.active_did_count }}</div>
            <div class="stat-sub">of {{ overview.metrics.did_count }} active</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-body">
            <div class="stat-label">Calls Today</div>
            <div class="stat-value">{{ overview.metrics.calls_today }}</div>
            <div class="stat-sub">{{ overview.metrics.call_count }} total calls</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-body">
            <div class="stat-label">Upcoming Appointments</div>
            <div class="stat-value">{{ overview.metrics.upcoming_appointments }}</div>
            <div class="stat-sub">Confirmed bookings</div>
          </div>
        </div>
      </div>

      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Customers &amp; Billing</h2>
          <span class="text-muted">{{ overview.customers.length }} accounts</span>
        </div>
        <p v-if="!overview.customers.length" class="empty-state">No customer accounts yet.</p>
        <div v-else class="table-scroll">
          <table class="table">
            <thead>
              <tr>
                <th>Business</th>
                <th>Email</th>
                <th>Plan</th>
                <th>Subscription</th>
                <th>Status</th>
                <th>Numbers</th>
                <th>Calls</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="customer in overview.customers" :key="customer.id">
                <td>{{ customer.name }}</td>
                <td>{{ customer.email }}</td>
                <td>{{ customer.plan }}</td>
                <td>
                  <span class="badge badge-info">{{ customer.subscription_status }}</span>
                  <div v-if="customer.plan_expires_at" class="text-muted">
                    Expires {{ formatDate(customer.plan_expires_at) }}
                  </div>
                </td>
                <td>{{ customer.status }}</td>
                <td>{{ customer.did_count }}</td>
                <td>{{ customer.call_count }}</td>
                <td>{{ formatDate(customer.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Allocated Phone Numbers</h2>
          <span class="text-muted">{{ overview.dids.length }} numbers</span>
        </div>
        <p v-if="!overview.dids.length" class="empty-state">No phone numbers allocated.</p>
        <div v-else class="table-scroll">
          <table class="table">
            <thead>
              <tr>
                <th>Number</th>
                <th>Customer</th>
                <th>Client Workspace</th>
                <th>Provider</th>
                <th>Connection</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="did in overview.dids" :key="did.id">
                <td class="font-mono">{{ did.number }}</td>
                <td>
                  <div>{{ did.customer_name }}</div>
                  <div class="text-muted">{{ did.customer_email }}</div>
                </td>
                <td>{{ did.client_workspace_name || "Unassigned" }}</td>
                <td>{{ did.provider }}</td>
                <td>{{ did.gateway_type }}</td>
                <td>{{ did.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card">
        <div class="card-header">
          <h2 class="card-title">Recent Business Activity</h2>
          <span class="text-muted">Latest calls and appointments</span>
        </div>
        <p v-if="!overview.recent_activity.length" class="empty-state">No business activity yet.</p>
        <div v-else class="table-scroll">
          <table class="table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Customer</th>
                <th>Activity</th>
                <th>Reference</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="activity in overview.recent_activity" :key="activity.id">
                <td>{{ activity.type }}</td>
                <td>{{ activity.customer_name }}</td>
                <td>{{ activity.detail }}</td>
                <td>{{ activity.reference || "—" }}</td>
                <td>{{ formatDate(activity.occurred_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
interface AdminMetrics {
  customer_count: number
  active_customer_count: number
  paid_customer_count: number
  did_count: number
  active_did_count: number
  call_count: number
  calls_today: number
  upcoming_appointments: number
}

interface AdminCustomer {
  id: number
  name: string
  email: string
  plan: string
  status: string
  subscription_status: string
  plan_expires_at: string | null
  created_at: string
  did_count: number
  call_count: number
}

interface AdminDid {
  id: number
  number: string
  provider: string
  status: string
  gateway_type: string
  customer_name: string
  customer_email: string
  client_workspace_name: string | null
}

interface AdminActivity {
  id: string
  type: "call" | "appointment"
  occurred_at: string
  customer_name: string
  detail: string
  reference: string | null
}

interface AdminOverview {
  metrics: AdminMetrics
  customers: AdminCustomer[]
  dids: AdminDid[]
  recent_activity: AdminActivity[]
}

const api = useApi()
const overview = ref<AdminOverview | null>(null)
const loading = ref(true)
const error = ref("")

async function loadOverview() {
  loading.value = true
  error.value = ""
  try {
    overview.value = await api.get<AdminOverview>("/admin/overview")
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Could not load platform data."
  } finally {
    loading.value = false
  }
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—"
}

onMounted(loadOverview)
</script>

<style scoped>
.admin-page {
  display: grid;
  gap: 24px;
}

.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.page-heading p {
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 16px;
}

.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: 13px;
}

.stat-value {
  color: var(--color-text);
  font-size: 28px;
  font-weight: 700;
  margin: 4px 0;
}

.stat-sub,
.text-muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

.card {
  min-width: 0;
}

.table-scroll {
  overflow-x: auto;
}

.table {
  min-width: 760px;
}

@media (max-width: 600px) {
  .page-heading {
    align-items: center;
  }
}
</style>
