<template>
  <div>
    <h1 class="page-title">Settings</h1>

    <div class="settings-grid">
      <!-- Receptionist Config -->
      <div class="card">
        <h2 class="section-title">Receptionist Configuration</h2>
        <form @submit.prevent="saveConfig">
          <div class="form-group">
            <label class="form-label">Welcome Message</label>
            <textarea v-model="config.welcome_message" class="form-control" rows="3" />
          </div>
          <div class="form-group">
            <label class="form-label">LLM Model</label>
            <input v-model="config.llm_model" class="form-control" placeholder="llama3.2:1b" />
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
          <div class="form-group">
            <label class="form-label">Voice</label>
            <input v-model="config.voice" class="form-control" placeholder="en_US-lessac-medium" />
          </div>
          <div class="form-group">
            <label class="form-label">Timezone</label>
            <input v-model="config.timezone" class="form-control" placeholder="America/New_York" />
          </div>
          <p v-if="configMsg" :class="['msg', configSaved ? 'msg-success' : 'msg-error']">{{ configMsg }}</p>
          <button type="submit" class="btn btn-primary" :disabled="configLoading">
            {{ configLoading ? "Saving…" : "Save Configuration" }}
          </button>
        </form>
      </div>

      <!-- Account -->
      <div class="card">
        <h2 class="section-title">Account</h2>
        <form @submit.prevent="saveAccount">
          <div class="form-group">
            <label class="form-label">Business Name</label>
            <input v-model="account.name" class="form-control" />
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input v-model="account.email" type="email" class="form-control" />
          </div>
          <div class="form-group">
            <label class="form-label">Plan</label>
            <span class="badge badge-info">{{ authStore.tenant?.plan }}</span>
          </div>
          <p v-if="accountMsg" :class="['msg', accountSaved ? 'msg-success' : 'msg-error']">{{ accountMsg }}</p>
          <button type="submit" class="btn btn-primary" :disabled="accountLoading">
            {{ accountLoading ? "Saving…" : "Save Account" }}
          </button>
        </form>

        <hr class="divider" />

        <h3 class="section-subtitle">API Key</h3>
        <div class="api-key-box">
          <code class="api-key">{{ showKey ? tenant?.api_key : "••••••••••••••••••••••••••••••••" }}</code>
          <button class="btn btn-outline" style="padding:4px 10px;font-size:12px" @click="showKey = !showKey">
            {{ showKey ? "Hide" : "Show" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const authStore = useAuthStore()

const tenant = ref<any>(null)
const showKey = ref(false)

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
  tenant.value = tenantRes
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
    configMsg.value   = "Configuration saved."
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
    accountMsg.value   = "Account updated."
  } catch (e: any) {
    accountSaved.value = false
    accountMsg.value   = e.message
  } finally {
    accountLoading.value = false
  }
}
</script>

<style scoped>
.page-title { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
.settings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.section-subtitle { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.msg { font-size: 13px; margin-bottom: 12px; }
.msg-success { color: var(--color-success); }
.msg-error   { color: var(--color-danger); }
.divider { border: none; border-top: 1px solid var(--color-border); margin: 20px 0; }
.api-key-box { display: flex; align-items: center; gap: 10px; background: var(--color-bg); padding: 10px; border-radius: var(--radius); }
.api-key { font-size: 13px; font-family: monospace; flex: 1; word-break: break-all; }
</style>
