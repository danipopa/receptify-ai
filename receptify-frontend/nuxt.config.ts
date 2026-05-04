// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-01-01",
  devtools: { enabled: true },

  devServer: { port: 3001 },

  modules: ["@pinia/nuxt"],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:3000/api/v1",
      // PayPal client ID is public — used by the PayPal JS SDK in the browser.
      // Set NUXT_PUBLIC_PAYPAL_CLIENT_ID in .env (sandbox or live).
      paypalClientId: process.env.NUXT_PUBLIC_PAYPAL_CLIENT_ID || "",
    },
  },

  app: {
    head: {
      title: "Receptify",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        { name: "description", content: "AI Phone Receptionist — Receptify" },
      ],
      link: [
        { rel: "icon", type: "image/x-icon", href: "/favicon.ico" },
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" },
        { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" },
      ],
    },
  },

  css: ["~/assets/css/main.css"],
})
