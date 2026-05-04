<template>
  <section class="lp-hero">
    <div class="lp-container lp-hero-inner">
      <!-- Copy -->
      <div>
        <div class="lp-hero-badge">
          <div class="lp-hero-badge-dot"></div>
          Live demo available — no credit card required
        </div>
        <h1 class="lp-hero-title">
          Your AI receptionist,<br>
          <span class="lp-hero-title-accent">always on call.</span>
        </h1>
        <p class="lp-hero-sub">
          Receptify answers every inbound call with natural, intelligent conversation —
          transcribes, summarizes, and routes — 24 hours a day, 7 days a week.
        </p>
        <div class="lp-hero-buttons">
          <NuxtLink to="/register" class="btn btn-primary btn-lg">
            Start for free →
          </NuxtLink>
          <a href="#how" class="btn btn-outline btn-lg">See how it works</a>
        </div>
        <p class="lp-hero-note">Free plan includes 50 calls/month. No credit card required.</p>
      </div>

      <!-- Phone mockup -->
      <div class="lp-hero-visual">
        <div style="position: relative;">
          <div class="lp-phone-card">
            <div class="lp-phone-header">
              <div class="lp-phone-dot active"></div>
              <div class="lp-phone-dot muted"></div>
              <span class="lp-phone-number">+1 (555) 012-3456</span>
              <span class="lp-phone-timer">0:42</span>
            </div>
            <div class="lp-phone-wave">
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
              <div class="lp-wave-bar"></div>
            </div>
            <div class="lp-transcript">
              <div class="lp-msg caller">"Hi, I'd like to book an appointment for next Tuesday."</div>
              <div class="lp-msg ai">"Of course! I have openings at 10 AM and 2 PM. Which works best for you?"</div>
              <div class="lp-msg caller">"2 PM would be perfect."</div>
              <div class="lp-typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
          <div class="lp-badge-float float-1">
            <span class="lp-float-icon">✅</span>
            <span>Appointment booked</span>
          </div>
          <div class="lp-badge-float float-2">
            <span class="lp-float-icon">📝</span>
            <span>Summary sent to CRM</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
