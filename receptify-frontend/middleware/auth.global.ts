const PUBLIC_PATHS = ["/", "/login", "/register"]

export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore()
  authStore.loadFromStorage()

  if (!authStore.isAuthenticated && !PUBLIC_PATHS.includes(to.path)) {
    return navigateTo("/login")
  }
  if (authStore.isAuthenticated && (to.path === "/login" || to.path === "/register")) {
    return navigateTo("/dashboard")
  }
  if (authStore.isAuthenticated && to.path === "/") {
    return navigateTo("/dashboard")
  }
})
