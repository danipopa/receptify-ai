<template>
  <div class="auth-wrapper">
    <!-- Left branding panel -->
    <div class="auth-brand">
      <div class="brand-logo">
        <div class="brand-mark">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" fill="currentColor"/>
          </svg>
        </div>
        <span class="brand-name">Receptify</span>
      </div>
      <div class="brand-hero">
        <h2 class="brand-headline">Your AI receptionist,<br>always on call.</h2>
        <p class="brand-sub">Never miss a customer. Receptify handles every inbound call with intelligent, natural conversation — 24 hours a day.</p>
      </div>
      <div class="brand-features">
        <div class="feature-item">
          <div class="feature-dot"></div>
          <span>AI-powered call handling</span>
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>
          <span>Real-time transcription &amp; summaries</span>
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>
          <span>Multi-DID routing per tenant</span>
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>
          <span>Full call logs &amp; analytics</span>
        </div>
      </div>
    </div>

    <!-- Right form panel -->
    <div class="auth-form-panel">
      <div class="auth-card">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  display: flex;
}

/* ── Left branding ── */
.auth-brand {
  flex: 1;
  background: linear-gradient(160deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
  padding: 48px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}
.auth-brand::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 70% 20%, rgba(99,102,241,.25) 0%, transparent 60%),
              radial-gradient(ellipse at 20% 80%, rgba(139,92,246,.15) 0%, transparent 50%);
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}
.brand-mark {
  width: 44px;
  height: 44px;
  background: rgba(255,255,255,.15);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.brand-mark svg { width: 24px; height: 24px; }
.brand-name { font-size: 22px; font-weight: 700; color: #fff; letter-spacing: -0.02em; }

.brand-hero { position: relative; }
.brand-headline {
  font-size: 36px;
  font-weight: 800;
  color: #fff;
  line-height: 1.2;
  letter-spacing: -0.03em;
  margin-bottom: 16px;
}
.brand-sub { font-size: 16px; color: #a5b4fc; line-height: 1.6; max-width: 380px; }

.brand-features { position: relative; display: flex; flex-direction: column; gap: 12px; }
.feature-item { display: flex; align-items: center; gap: 12px; color: #c7d2fe; font-size: 14px; font-weight: 500; }
.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #818cf8;
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(129,140,248,.6);
}

/* ── Right form panel ── */
.auth-form-panel {
  width: 480px;
  flex-shrink: 0;
  background: var(--color-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 32px;
}
.auth-card {
  width: 100%;
  max-width: 380px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 40px 36px;
  box-shadow: var(--shadow-xl);
}

@media (max-width: 768px) {
  .auth-brand { display: none; }
  .auth-form-panel { width: 100%; }
}
</style>
