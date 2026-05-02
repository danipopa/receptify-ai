<template>
  <div class="auth-wrapper">
    <div class="auth-card card">
      <div class="auth-logo">
        <span class="logo-text">Receptify</span>
      </div>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
}
.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 40px;
}
.auth-logo {
  text-align: center;
  margin-bottom: 32px;
}
.logo-text {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-primary);
}
</style>
