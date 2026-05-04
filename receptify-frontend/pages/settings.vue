<template>
  <div>
    <!-- Tabs -->
    <div class="tabs">
      <button :class="['tab-btn', activeTab === 'receptionist' && 'active']" @click="activeTab = 'receptionist'">
        Receptionist
      </button>
      <button :class="['tab-btn', activeTab === 'account' && 'active']" @click="activeTab = 'account'">
        Account
      </button>
      <button :class="['tab-btn', activeTab === 'api' && 'active']" @click="activeTab = 'api'">
        API Access
      </button>
      <button :class="['tab-btn', activeTab === 'billing' && 'active']" @click="openBillingTab">
        Billing
      </button>
    </div>

    <!-- Receptionist tab -->
    <div v-if="activeTab === 'receptionist'" class="tab-pane">
      <div class="settings-section">
        <div class="settings-aside">
          <h3 class="section-heading">AI Configuration</h3>
          <p class="section-desc">Configure how your AI receptionist speaks, thinks, and responds to callers.</p>
        </div>
        <div class="card settings-card">
          <div v-if="configMsg" :class="['alert', configSaved ? 'alert-success' : 'alert-error']">
            {{ configMsg }}
          </div>
          <form @submit.prevent="saveConfig">
            <div class="form-group">
              <label class="form-label">Welcome Message</label>
              <textarea v-model="config.welcome_message" class="form-control" rows="3" placeholder="Hello! Thank you for calling. How can I help you today?" />
              <span class="form-hint">This is the first thing callers will hear.</span>
            </div>
            <div class="form-group">
              <label class="form-label">LLM Model</label>
              <input v-model="config.llm_model" class="form-control" placeholder="llama3.2:1b" />
              <span class="form-hint">Ollama model name to use for generating responses.</span>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">RAG Chunk Words</label>
                <input v-model.number="config.rag_chunk_words" type="number" class="form-control" min="10" max="200" />
              </div>
              <div class="form-group">
                <label class="form-label">RAG Top-K</label>
                <input v-model.number="config.rag_top_k" type="number" class="form-control" min="1" max="10" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Voice</label>
                <input v-model="config.voice" class="form-control" placeholder="en_US-lessac-medium" />
              </div>
              <div class="form-group">
                <label class="form-label">Timezone</label>
                <input v-model="config.timezone" class="form-control" placeholder="America/New_York" />
              </div>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="configLoading">
                <svg v-if="configLoading" class="spin-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" style="opacity:.25"/>
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" style="opacity:.75"/>
                </svg>
                {{ configLoading ? "Saving…" : "Save Configuration" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Account tab -->
    <div v-if="activeTab === 'account'" class="tab-pane">
      <div class="settings-section">
        <div class="settings-aside">
          <h3 class="section-heading">Business Details</h3>
          <p class="section-desc">Update your business name and email address associated with this account.</p>
        </div>
        <div class="card settings-card">
          <div v-if="accountMsg" :class="['alert', accountSaved ? 'alert-success' : 'alert-error']">
            {{ accountMsg }}
          </div>
          <form @submit.prevent="saveAccount">
            <div class="form-group">
              <label class="form-label">Business Name</label>
              <input v-model="account.name" class="form-control" placeholder="Acme Corp" />
            </div>
            <div class="form-group">
              <label class="form-label">Email Address</label>
              <input v-model="account.email" type="email" class="form-control" />
            </div>
            <div class="form-group">
              <label class="form-label">Plan</label>
              <div class="plan-display">
                <span class="badge badge-info plan-badge">
                  {{ authStore.tenant?.plan }} plan
                </span>
                <span class="plan-hint">Contact us to upgrade</span>
              </div>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="accountLoading">
                {{ accountLoading ? "Saving…" : "Save Changes" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Billing tab -->
    <div v-if="activeTab === 'billing'" class="tab-pane">
      <div class="settings-section">
        <div class="settings-aside">
          <h3 class="section-heading">Subscription</h3>
          <p class="section-desc">Manage your Receptify plan. Payments are processed securely by PayPal — no card data touches our servers.</p>
        </div>
        <div class="card settings-card">
          <div v-if="billingError" class="alert alert-error" style="margin-bottom:20px">{{ billingError }}</div>
          <div v-if="billingLoading" class="billing-loading">Loading billing info…</div>

          <template v-else-if="billing">
            <!-- Current plan banner -->
            <div class="current-plan-banner">
              <div class="current-plan-left">
                <div class="current-plan-label">Current plan</div>
                <div class="current-plan-name">{{ billing.plan.charAt(0).toUpperCase() + billing.plan.slice(1) }}</div>
                <div v-if="billing.plan_expires_at" class="current-plan-expires">
                  Access until {{ new Date(billing.plan_expires_at).toLocaleDateString() }}
                </div>
              </div>
              <span :class="['badge', billing.plan === 'free' ? 'badge-neutral' : 'badge-success']">{{ billing.subscription_status }}</span>
            </div>

            <!-- Upgrade cards -->
            <div v-if="billing.plan === 'free'" class="billing-plans">
              <!-- Pro plan -->
              <div v-if="billing.paypal_plan_ids.pro" class="billing-plan-card billing-plan-pro">
                <div class="billing-plan-header">
                  <div>
                    <div class="billing-plan-name">Pro</div>
                    <div class="billing-plan-price">$29<span>/month</span></div>
                  </div>
                  <span class="badge badge-info">Most popular</span>
                </div>
                <ul class="billing-plan-features">
                  <li>✓ Up to 5 DIDs</li>
                  <li>✓ 500 calls / month</li>
                  <li>✓ RAG knowledge base</li>
                  <li>✓ Custom voice &amp; wake phrase</li>
                  <li>✓ Priority support</li>
                </ul>
                <div :id="'paypal-btn-pro'" class="paypal-btn-container"></div>
              </div>

              <!-- Starter plan -->
              <div v-if="billing.paypal_plan_ids.starter" class="billing-plan-card">
                <div class="billing-plan-header">
                  <div>
                    <div class="billing-plan-name">Starter</div>
                    <div class="billing-plan-price">$9<span>/month</span></div>
                  </div>
                </div>
                <ul class="billing-plan-features">
                  <li>✓ 1 DID</li>
                  <li>✓ 150 calls / month</li>
                  <li>✓ Full transcription</li>
                </ul>
                <div :id="'paypal-btn-starter'" class="paypal-btn-container"></div>
              </div>
            </div>

            <!-- Active paid plan — show cancellation -->
            <div v-if="billing.plan !== 'free' && billing.subscription_status === 'active'" class="billing-active-section">
              <p class="billing-active-msg">You're on the <strong>{{ billing.plan }}</strong> plan. Your subscription renews automatically via PayPal.</p>
              <button class="btn btn-danger btn-sm" :disabled="cancelLoading" @click="handleCancel">
                {{ cancelLoading ? 'Cancelling…' : 'Cancel subscription' }}
              </button>
              <p v-if="cancelMsg" class="billing-cancel-note">{{ cancelMsg }}</p>
            </div>

            <!-- No PayPal plans configured -->
            <div v-if="billing.plan === 'free' && !billing.paypal_plan_ids.pro && !billing.paypal_plan_ids.starter" class="billing-unconfigured">
              <p>Upgrade plans will appear here once PayPal is configured. Contact <a href="mailto:hello@receptify.us">hello@receptify.us</a> to upgrade.</p>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- API Access tab -->
    <div v-if="activeTab === 'api'" class="tab-pane">
      <div class="settings-section">
        <div class="settings-aside">
          <h3 class="section-heading">API Key</h3>
          <p class="section-desc">Use this key to authenticate requests to the Receptify API. Keep it secret.</p>
        </div>
        <div class="card settings-card">
          <div class="api-key-section">
            <label class="form-label" style="margin-bottom:8px;display:block">Your API Key</label>
            <div class="api-key-box">
              <code class="api-key-value font-mono">{{ showKey ? tenant?.api_key : "rfy_" + "•".repeat(32) }}</code>
              <button class="btn btn-outline btn-sm" type="button" @click="showKey = !showKey">
                <svg v-if="!showKey" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" style="width:15px;height:15px">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" style="width:15px;height:15px">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                </svg>
                {{ showKey ? "Hide" : "Reveal" }}
              </button>
              <button v-if="showKey && tenant?.api_key" class="btn btn-outline btn-sm" type="button" @click="copyKey">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" style="width:15px;height:15px">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
                </svg>
                {{ copied ? "Copied!" : "Copy" }}
              </button>
            </div>
            <p class="api-warning">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" style="width:14px;height:14px;flex-shrink:0">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              Treat this key like a password. Never expose it in client-side code or public repositories.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const authStore = useAuthStore()
const runtimeConfig = useRuntimeConfig()
const { billing, loading: billingLoading, error: billingError, fetchBilling, confirmSubscription, cancelSubscription } = useBilling()
const cancelLoading = ref(false)
const cancelMsg = ref("")
let paypalLoaded = false

const activeTab = ref<"receptionist" | "account" | "api" | "billing">("receptionist")
const tenant = ref<any>(null)
const showKey = ref(false)
const copied = ref(false)

const config = reactive({
  welcome_message: "",
  llm_model: "",
  rag_chunk_words: 30,
  rag_top_k: 4,
  voice: "",
  timezone: "",
})
const configLoading = ref(false)
const configMsg     = ref("")
const configSaved   = ref(false)

const account = reactive({ name: "", email: "" })
const accountLoading = ref(false)
const accountMsg     = ref("")
const accountSaved   = ref(false)

onMounted(async () => {
  const [tenantRes, configRes] = await Promise.all([
    api.get<any>("/tenant"),
    api.get<any>("/tenant_config"),
  ])
  tenant.value  = tenantRes
  account.name  = tenantRes.name
  account.email = tenantRes.email
  Object.assign(config, configRes)
})

async function saveConfig() {
  configMsg.value = ""
  configLoading.value = true
  try {
    await api.patch("/tenant_config", config)
    configSaved.value = true
    configMsg.value   = "Configuration saved successfully."
  } catch (e: any) {
    configSaved.value = false
    configMsg.value   = e.message
  } finally {
    configLoading.value = false
  }
}

async function saveAccount() {
  accountMsg.value = ""
  accountLoading.value = true
  try {
    const updated = await api.patch<any>("/tenant", account)
    authStore.tenant!.name  = updated.name
    authStore.tenant!.email = updated.email
    accountSaved.value = true
    accountMsg.value   = "Account updated successfully."
  } catch (e: any) {
    accountSaved.value = false
    accountMsg.value   = e.message
  } finally {
    accountLoading.value = false
  }
}

async function openBillingTab() {
  activeTab.value = "billing"
  if (!billing.value) await fetchBilling()
  if (billing.value && runtimeConfig.public.paypalClientId) {
    await nextTick()
    loadPayPalSDK()
  }
}

function loadPayPalSDK() {
  if (paypalLoaded || !runtimeConfig.public.paypalClientId) return
  paypalLoaded = true
  const script = document.createElement("script")
  script.src = `https://www.paypal.com/sdk/js?client-id=${runtimeConfig.public.paypalClientId}&vault=true&intent=subscription`
  script.onload = () => renderPayPalButtons()
  document.head.appendChild(script)
}

function renderPayPalButtons() {
  const w = window as any
  if (!w.paypal || !billing.value) return
  const planIds = billing.value.paypal_plan_ids
  const mount = (planKey: "pro" | "starter", containerId: string) => {
    const el = document.getElementById(containerId)
    if (!el || !planIds[planKey]) return
    el.innerHTML = ""
    w.paypal.Buttons({
      style: { shape: "rect", color: "blue", layout: "vertical", label: "subscribe" },
      createSubscription: (_data: any, actions: any) => actions.subscription.create({ plan_id: planIds[planKey] }),
      onApprove: async (data: any) => {
        try {
          await confirmSubscription(data.subscriptionID)
        } catch (e: any) {
          billingError.value = e.message
        }
      },
      onError: (err: any) => { billingError.value = String(err) },
    }).render(`#${containerId}`)
  }
  mount("pro", "paypal-btn-pro")
  mount("starter", "paypal-btn-starter")
}

async function handleCancel() {
  if (!confirm("Cancel your subscription? You'll keep access until end of the billing period.")) return
  cancelLoading.value = true
  cancelMsg.value = ""
  try {
    await cancelSubscription()
    cancelMsg.value = "Subscription cancelled. You'll retain access until end of month."
  } catch (e: any) {
    cancelMsg.value = e.message
  } finally {
    cancelLoading.value = false
  }
}

async function copyKey() {
  if (tenant.value?.api_key) {
    await navigator.clipboard.writeText(tenant.value.api_key)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}
</script>

<style scoped>
.tab-pane { animation: fadeIn 0.15s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

.settings-section {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 32px;
  align-items: start;
}
.settings-aside { padding-top: 4px; }
.section-heading { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
.section-desc { font-size: 13px; color: var(--color-text-muted); line-height: 1.6; }
.settings-card { flex: 1; }

.form-actions { margin-top: 8px; padding-top: 20px; border-top: 1px solid var(--color-border); }

.plan-display { display: flex; align-items: center; gap: 12px; margin-top: 2px; }
.plan-badge   { font-size: 13px; padding: 5px 14px; }
.plan-hint    { font-size: 13px; color: var(--color-text-muted); }

/* API key */
.api-key-section {}
.api-key-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8fafc;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-bottom: 12px;
}
.api-key-value {
  flex: 1;
  font-size: 13px;
  letter-spacing: 0.02em;
  color: var(--color-text);
  word-break: break-all;
}
/* Billing */
.billing-loading { color: var(--color-text-muted); font-size: 14px; padding: 20px 0; }
.current-plan-banner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  margin-bottom: 28px;
}
.current-plan-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: var(--color-text-muted); margin-bottom: 4px; }
.current-plan-name  { font-size: 22px; font-weight: 800; color: var(--color-text); }
.current-plan-expires { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }

.billing-plans {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 16px;
}
.billing-plan-card {
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
}
.billing-plan-pro { border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(79,70,229,.08); }
.billing-plan-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.billing-plan-name  { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--color-text-muted); margin-bottom: 4px; }
.billing-plan-price { font-size: 32px; font-weight: 900; color: var(--color-text); letter-spacing: -.03em; }
.billing-plan-price span { font-size: 14px; font-weight: 500; color: var(--color-text-muted); }
.billing-plan-features { list-style: none; display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; font-size: 13px; color: var(--color-text-muted); }
.paypal-btn-container { min-height: 45px; }

.billing-active-section { padding-top: 8px; }
.billing-active-msg  { font-size: 14px; color: var(--color-text-muted); margin-bottom: 16px; }
.billing-cancel-note { margin-top: 12px; font-size: 13px; color: var(--color-text-muted); }
.billing-unconfigured { font-size: 14px; color: var(--color-text-muted); }
.billing-unconfigured a { color: var(--color-primary); }

.api-warning {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #92400e;
  background: var(--color-warning-bg);
  border: 1px solid #fde68a;
  border-radius: var(--radius);
  padding: 10px 12px;
}

/* Spinner */
.spin-icon { animation: spin 0.8s linear infinite; width: 15px; height: 15px; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .settings-section { grid-template-columns: 1fr; gap: 16px; }
}
</style>
