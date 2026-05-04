<template>
  <div class="app-shell">
    <aside class="sidebar">
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="logo-mark">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" fill="currentColor"/>
          </svg>
        </div>
        <span class="logo-text">Receptify</span>
      </div>

      <!-- Nav -->
      <nav class="sidebar-nav">
        <div class="nav-section-label">Workspace</div>
        <NuxtLink to="/dashboard" class="nav-item">
          <svg class="nav-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
          </svg>
          <span>Dashboard</span>
        </NuxtLink>

        <NuxtLink to="/dids" class="nav-item">
          <svg class="nav-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
          </svg>
          <span>Phone Numbers</span>
        </NuxtLink>

        <NuxtLink to="/call-logs" class="nav-item">
          <svg class="nav-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </svg>
          <span>Call Logs</span>
        </NuxtLink>

        <div class="nav-section-label" style="margin-top:8px">Configuration</div>
        <NuxtLink to="/settings" class="nav-item">
          <svg class="nav-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>Settings</span>
        </NuxtLink>
      </nav>

      <!-- User footer -->
      <div class="sidebar-footer">
        <div class="sidebar-user">
          <div class="user-avatar">{{ initials }}</div>
          <div class="user-meta">
            <div class="user-name">{{ authStore.tenant?.name }}</div>
            <div class="user-plan">{{ authStore.tenant?.plan }} plan</div>
          </div>
        </div>
        <button class="btn btn-ghost btn-sm sign-out-btn" @click="logout">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" style="width:15px;height:15px">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
          </svg>
          Sign out
        </button>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <h1 class="topbar-title">{{ pageTitle }}</h1>
        </div>
        <div class="topbar-right">
          <div class="topbar-badge">
            <span class="badge badge-info">{{ authStore.tenant?.plan }}</span>
          </div>
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

const initials = computed(() => {
  const name = authStore.tenant?.name || ""
  return name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase() || "?"
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

/* ── Sidebar ── */
.sidebar {
  width: var(--sidebar-width);
  background: var(--sidebar-bg);
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  height: 100vh;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px;
  border-bottom: 1px solid rgba(255,255,255,.06);
}
.logo-mark {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #4f46e5, #818cf8);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.logo-mark svg { width: 18px; height: 18px; }
.logo-text { font-size: 17px; font-weight: 700; color: #fff; letter-spacing: -0.01em; }

.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  overflow-y: auto;
}
.nav-section-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #475569;
  padding: 10px 10px 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  transition: background 0.12s, color 0.12s;
  text-decoration: none;
  margin-bottom: 2px;
}
.nav-item:hover { background: rgba(255,255,255,.06); color: #cbd5e1; text-decoration: none; }
.nav-item.router-link-active {
  background: rgba(79,70,229,.25);
  color: #a5b4fc;
}
.nav-item.router-link-active .nav-icon { color: #818cf8; }
.nav-icon { width: 18px; height: 18px; flex-shrink: 0; }

/* ── Sidebar footer ── */
.sidebar-footer {
  padding: 14px 12px;
  border-top: 1px solid rgba(255,255,255,.06);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
}
.user-avatar {
  width: 34px;
  height: 34px;
  background: linear-gradient(135deg, #4f46e5, #818cf8);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.user-meta { min-width: 0; }
.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-plan { font-size: 11px; color: #64748b; text-transform: capitalize; }
.sign-out-btn { color: #64748b; font-size: 12px; justify-content: flex-start; }
.sign-out-btn:hover { color: #94a3b8 !important; }

/* ── Main area ── */
.main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }

.topbar {
  height: var(--topbar-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  flex-shrink: 0;
  box-shadow: 0 1px 0 var(--color-border);
}
.topbar-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.02em;
}
.topbar-right { display: flex; align-items: center; gap: 12px; }

.content {
  flex: 1;
  padding: 28px;
  overflow-y: auto;
  background: var(--color-bg);
}
</style>
