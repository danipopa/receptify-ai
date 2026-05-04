<template>
  <section class="lp-section" id="pricing">
    <div class="lp-container lp-text-center">
      <div class="lp-eyebrow">
        <div class="lp-eyebrow-dot"></div>
        Pricing
      </div>
      <h2 class="lp-section-title">Simple, transparent pricing</h2>
      <p class="lp-section-sub">Start free. Scale as you grow. No hidden fees, no per-minute surprises.</p>

      <div class="lp-pricing-grid">
        <!-- Free -->
        <div class="lp-pricing-card">
          <div class="lp-plan-name">Free</div>
          <div class="lp-plan-price">
            <span class="lp-plan-price-currency">$</span>
            <span class="lp-plan-price-amount">0</span>
            <span class="lp-plan-price-period">/month</span>
          </div>
          <p class="lp-plan-desc">Perfect for testing Receptify on a single phone number.</p>
          <ul class="lp-plan-features">
            <li><span class="lp-check">✓</span> 1 DID (phone number)</li>
            <li><span class="lp-check">✓</span> 50 calls per month</li>
            <li><span class="lp-check">✓</span> Full transcription</li>
            <li><span class="lp-check">✓</span> Call summaries</li>
            <li><span class="lp-check">✓</span> Dashboard access</li>
            <li class="na"><span>—</span> RAG knowledge base</li>
            <li class="na"><span>—</span> Custom voice</li>
          </ul>
          <NuxtLink to="/register" class="btn btn-outline">Get started free</NuxtLink>
        </div>

        <!-- Pro -->
        <div class="lp-pricing-card popular">
          <div class="lp-popular-badge">⭐ Most popular</div>
          <div class="lp-plan-name">Pro</div>
          <div class="lp-plan-price">
            <span class="lp-plan-price-currency">$</span>
            <span class="lp-plan-price-amount">29</span>
            <span class="lp-plan-price-period">/month</span>
          </div>
          <p class="lp-plan-desc">Everything you need to run a professional AI receptionist.</p>
          <ul class="lp-plan-features">
            <li><span class="lp-check">✓</span> Up to 5 DIDs</li>
            <li><span class="lp-check">✓</span> 500 calls per month</li>
            <li><span class="lp-check">✓</span> Full transcription</li>
            <li><span class="lp-check">✓</span> Call summaries</li>
            <li><span class="lp-check">✓</span> RAG knowledge base</li>
            <li><span class="lp-check">✓</span> Custom voice &amp; wake phrase</li>
            <li><span class="lp-check">✓</span> Priority support</li>
          </ul>
          <NuxtLink to="/register" class="btn btn-primary">Start Pro free for 14 days</NuxtLink>
        </div>

        <!-- Enterprise -->
        <div class="lp-pricing-card">
          <div class="lp-plan-name">Enterprise</div>
          <div class="lp-plan-price">
            <span class="lp-plan-price-amount" style="font-size: 36px; margin-top: 8px;">Custom</span>
          </div>
          <p class="lp-plan-desc">Unlimited scale, dedicated infrastructure, and white-label options.</p>
          <ul class="lp-plan-features">
            <li><span class="lp-check">✓</span> Unlimited DIDs</li>
            <li><span class="lp-check">✓</span> Unlimited calls</li>
            <li><span class="lp-check">✓</span> Dedicated LLM instance</li>
            <li><span class="lp-check">✓</span> White-label branding</li>
            <li><span class="lp-check">✓</span> CRM &amp; Zapier integrations</li>
            <li><span class="lp-check">✓</span> SLA with 99.9% uptime</li>
            <li><span class="lp-check">✓</span> Dedicated account manager</li>
          </ul>
          <a href="mailto:hello@receptify.us" class="btn btn-outline">Contact sales</a>
        </div>
      </div>
    </div>
  </section>
</template>
