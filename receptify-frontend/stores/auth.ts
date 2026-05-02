import { defineStore } from "pinia"

interface Tenant {
  id: number
  name: string
  subdomain: string
  email: string
  plan: string
  status: string
}

interface AuthState {
  token: string | null
  tenant: Tenant | null
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    token: null,
    tenant: null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    setAuth(token: string, tenant: Tenant) {
      this.token = token
      this.tenant = tenant
      if (import.meta.client) {
        localStorage.setItem("auth_token", token)
        localStorage.setItem("auth_tenant", JSON.stringify(tenant))
      }
    },

    loadFromStorage() {
      if (!import.meta.client) return
      const token = localStorage.getItem("auth_token")
      const tenant = localStorage.getItem("auth_tenant")
      if (token && tenant) {
        this.token = token
        this.tenant = JSON.parse(tenant)
      }
    },

    logout() {
      this.token = null
      this.tenant = null
      if (import.meta.client) {
        localStorage.removeItem("auth_token")
        localStorage.removeItem("auth_tenant")
      }
    },
  },
})
