<template>
  <section class="lp-section lp-investor-bg" id="investors">
    <div class="lp-container">
      <!-- Header -->
      <div class="lp-text-center" style="margin-bottom: 64px;">
        <div class="lp-eyebrow" style="background: rgba(129,140,248,.15); color: #a5b4fc;">
          <div class="lp-eyebrow-dot" style="background: #a5b4fc;"></div>
          Investor brief
        </div>
        <h2 class="lp-section-title">A $50B market still being answered by voicemail</h2>
        <p class="lp-section-sub">Small businesses lose over $75B annually from missed calls. Receptify eliminates the problem entirely.</p>
      </div>

      <!-- Problem / Solution -->
      <div class="lp-problem-solution">
        <div class="lp-ps-card problem">
          <div class="lp-ps-label problem-label">❌ The Problem</div>
          <h3>Businesses can't afford to miss a single call</h3>
          <ul>
            <li><span>•</span><span><strong style="color: #f1f5f9;">62% of callers</strong> won't leave a voicemail — they hang up and call a competitor.</span></li>
            <li><span>•</span><span>Hiring a full-time receptionist costs <strong style="color: #f1f5f9;">$38,000–$55,000/year</strong> — prohibitive for SMBs.</span></li>
            <li><span>•</span><span>Existing IVR systems are rigid, frustrating, and <strong style="color: #f1f5f9;">damage brand perception</strong>.</span></li>
            <li><span>•</span><span>After-hours calls — which represent <strong style="color: #f1f5f9;">35% of total volume</strong> — are almost entirely unanswered.</span></li>
          </ul>
        </div>
        <div class="lp-ps-card solution">
          <div class="lp-ps-label solution-label">✅ Our Solution</div>
          <h3>An AI receptionist that costs less than a coffee a day</h3>
          <ul>
            <li><span>•</span><span>Answers <strong style="color: #e0e7ff;">100% of calls</strong>, 24/7, with natural language understanding.</span></li>
            <li><span>•</span><span>Deploy in <strong style="color: #e0e7ff;">under 5 minutes</strong> — no developers, no hardware, no training data.</span></li>
            <li><span>•</span><span>Each tenant gets a <strong style="color: #e0e7ff;">fully isolated AI</strong> configured with their own business knowledge.</span></li>
            <li><span>•</span><span>Starting at <strong style="color: #e0e7ff;">$29/month</strong> — 100× cheaper than a human receptionist.</span></li>
          </ul>
        </div>
      </div>

      <!-- Traction -->
      <div class="lp-text-center" style="margin-bottom: 32px;">
        <h3 style="color: #f1f5f9; font-size: 24px; font-weight: 800; margin-bottom: 8px;">Early traction</h3>
        <p style="color: #64748b; font-size: 15px;">Metrics at product launch — May 2026</p>
      </div>
      <div class="lp-traction-grid">
        <div class="lp-traction-card">
          <div class="lp-traction-number">Day 1</div>
          <div class="lp-traction-label">Product launched</div>
        </div>
        <div class="lp-traction-card">
          <div class="lp-traction-number">$0</div>
          <div class="lp-traction-label">Infrastructure cost at free tier</div>
        </div>
        <div class="lp-traction-card">
          <div class="lp-traction-number">5 min</div>
          <div class="lp-traction-label">Avg. onboarding time</div>
        </div>
      </div>

      <!-- Market opportunity -->
      <div class="lp-market-row">
        <div class="lp-market-text">
          <h3>A $50B total addressable market</h3>
          <p>33 million small businesses in the US alone — the vast majority have no automated call handling. Receptify is the first solution built for the post-LLM era.</p>
          <div class="lp-market-items">
            <div class="lp-market-item">
              <div class="lp-market-item-dot"></div>
              <span>TAM: $50B — US SMB phone answering services</span>
            </div>
            <div class="lp-market-item">
              <div class="lp-market-item-dot"></div>
              <span>SAM: $8B — Businesses with 1–50 employees</span>
            </div>
            <div class="lp-market-item">
              <div class="lp-market-item-dot"></div>
              <span>SOM: $400M — Tech-forward SMBs reachable digitally</span>
            </div>
          </div>
        </div>

        <div ref="marketVisual" class="lp-market-visual">
          <div class="lp-market-bar-row">
            <div class="lp-market-bar-item">
              <div class="lp-market-bar-label">
                <span>TAM</span><span>$50B</span>
              </div>
              <div class="lp-market-bar-track">
                <div class="lp-market-bar-fill" :style="{ width: animated ? '100%' : '0' }"></div>
              </div>
            </div>
            <div class="lp-market-bar-item">
              <div class="lp-market-bar-label">
                <span>SAM</span><span>$8B</span>
              </div>
              <div class="lp-market-bar-track">
                <div class="lp-market-bar-fill" :style="{ width: animated ? '16%' : '0' }"></div>
              </div>
            </div>
            <div class="lp-market-bar-item">
              <div class="lp-market-bar-label">
                <span>SOM</span><span>$400M</span>
              </div>
              <div class="lp-market-bar-track">
                <div class="lp-market-bar-fill" :style="{ width: animated ? '0.8%' : '0' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
const marketVisual = ref<HTMLElement | null>(null)
const animated = ref(false)

onMounted(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setTimeout(() => { animated.value = true }, 100)
          observer.disconnect()
        }
      })
    },
    { threshold: 0.3 }
  )
  if (marketVisual.value) observer.observe(marketVisual.value)
})
</script>
