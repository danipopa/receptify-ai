<template>
  <div class="landing-page">
    <LandingNav />
    <LandingHero />
    <LandingStats />
    <LandingHowItWorks />
    <LandingFeatures />
    <LandingInvestors />
    <LandingPricing />
    <LandingTeam />
    <LandingCta />
    <LandingFooter />
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })
</script>

<style>
@import '~/assets/css/landing.css';
</style>
