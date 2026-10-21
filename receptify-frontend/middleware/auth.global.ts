const PUBLIC_PATHS = ["/", "/login", "/register"]

export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore()
  authStore.loadFromStorage()

  if (!authStore.isAuthenticated && !PUBLIC_PATHS.includes(to.path)) {
    return navigateTo("/login")
  }
  if (authStore.isAuthenticated) {
    const landingPage = authStore.tenant?.platform_admin ? "/admin" : "/dashboard"

    if (to.path === "/login" || to.path === "/register" || to.path === "/") {
      return navigateTo(landingPage)
    }
    if (authStore.tenant?.platform_admin && to.path !== "/admin") {
      return navigateTo("/admin")
    }
    if (!authStore.tenant?.platform_admin && to.path === "/admin") {
      return navigateTo("/dashboard")
    }
  }
})
