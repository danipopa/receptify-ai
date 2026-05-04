<template>
  <nav class="lp-nav">
    <div class="lp-container lp-nav-inner">
      <NuxtLink to="/" class="lp-nav-logo">
        <div class="lp-nav-logo-mark">R</div>
        Receptify
      </NuxtLink>

      <ul class="lp-nav-links">
        <li><a href="#how">How it works</a></li>
        <li><a href="#features">Features</a></li>
        <li><a href="#investors">Investors</a></li>
        <li><a href="#pricing">Pricing</a></li>
      </ul>

      <div class="lp-nav-cta">
        <NuxtLink to="/login" class="btn btn-outline btn-sm">Sign in</NuxtLink>
        <NuxtLink to="/register" class="btn btn-primary btn-sm">Start free</NuxtLink>
      </div>
    </div>
  </nav>
</template>
