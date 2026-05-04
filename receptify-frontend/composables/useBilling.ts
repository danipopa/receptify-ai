// Composable for billing / PayPal subscription management.
export function useBilling() {
  const api = useApi()

  const billing = ref<{
    plan: string
    subscription_id: string | null
    subscription_status: string
    plan_expires_at: string | null
    paypal_plan_ids: Record<string, string>
  } | null>(null)

  const loading = ref(false)
  const error = ref("")

  async function fetchBilling() {
    loading.value = true
    error.value = ""
    try {
      billing.value = await api.get<any>("/billing")
    } catch (e: any) {
      error.value = e.message || "Failed to load billing info"
    } finally {
      loading.value = false
    }
  }

  async function confirmSubscription(subscriptionId: string) {
    const data = await api.post<any>("/billing/confirm", { subscription_id: subscriptionId })
    if (billing.value) {
      billing.value.plan = data.plan
      billing.value.subscription_id = data.subscription_id
      billing.value.subscription_status = data.subscription_status
    }
    return data
  }

  async function cancelSubscription() {
    const data = await api.delete<any>("/billing")
    if (billing.value) {
      billing.value.plan = data.plan
      billing.value.subscription_status = data.subscription_status
      billing.value.plan_expires_at = data.plan_expires_at
    }
    return data
  }

  return { billing, loading, error, fetchBilling, confirmSubscription, cancelSubscription }
}
