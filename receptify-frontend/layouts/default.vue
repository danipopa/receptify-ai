<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-logo">
        <span class="logo-text">Receptify</span>
      </div>
      <nav class="sidebar-nav">
        <NuxtLink to="/dashboard" class="nav-item">
          <span class="nav-icon">⊞</span> Dashboard
        </NuxtLink>
        <NuxtLink to="/dids" class="nav-item">
          <span class="nav-icon">☎</span> Phone Numbers
        </NuxtLink>
        <NuxtLink to="/call-logs" class="nav-item">
          <span class="nav-icon">📋</span> Call Logs
        </NuxtLink>
        <NuxtLink to="/settings" class="nav-item">
          <span class="nav-icon">⚙</span> Settings
        </NuxtLink>
      </nav>
      <div class="sidebar-footer">
        <button class="btn btn-outline" style="width:100%" @click="logout">Sign out</button>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <span class="topbar-title">{{ pageTitle }}</span>
        <div class="topbar-right">
          <span class="tenant-name">{{ authStore.tenant?.name }}</span>
        </div>
      </header>
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from "~/stores/auth"

const authStore = useAuthStore()
const route = useRoute()

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    "/dashboard":  "Dashboard",
    "/dids":       "Phone Numbers",
    "/call-logs":  "Call Logs",
    "/settings":   "Settings",
  }
  return map[route.path] ?? "Receptify"
})

async function logout() {
  authStore.logout()
  await navigateTo("/login")
}
</script>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background: #1b1a19;
  color: #d2d0ce;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-logo {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid #3b3a39;
}
.logo-text { font-size: 18px; font-weight: 700; color: #fff; }

.sidebar-nav {
  flex: 1;
  padding: 8px 0;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  color: #d2d0ce;
  font-size: 14px;
  transition: background 0.1s;
  text-decoration: none;
}
.nav-item:hover { background: #3b3a39; color: #fff; }
.nav-item.router-link-active { background: #0078d4; color: #fff; }
.nav-icon { width: 16px; text-align: center; }

.sidebar-footer { padding: 16px; }

/* Main area */
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.topbar {
  height: var(--topbar-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}
.topbar-title { font-size: 16px; font-weight: 600; }
.tenant-name { font-size: 14px; color: var(--color-text-muted); }

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>
