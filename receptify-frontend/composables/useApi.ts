export function useApi() {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  async function request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    }
    if (authStore.token) {
      headers["Authorization"] = `Bearer ${authStore.token}`
    }

    const response = await fetch(`${config.public.apiBase}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error || error.errors?.join(", ") || `HTTP ${response.status}`)
    }

    if (response.status === 204) return undefined as T
    return response.json()
  }

  return {
    get:    <T>(url: string) => request<T>(url),
    post:   <T>(url: string, body: unknown) => request<T>(url, { method: "POST",   body: JSON.stringify(body) }),
    patch:  <T>(url: string, body: unknown) => request<T>(url, { method: "PATCH",  body: JSON.stringify(body) }),
    delete: <T>(url: string)               => request<T>(url, { method: "DELETE" }),
  }
}
