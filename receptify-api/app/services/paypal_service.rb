# frozen_string_literal: true

# Thin wrapper around the PayPal REST API v1 (Subscriptions).
#
# Required env vars:
#   PAYPAL_CLIENT_ID      – OAuth2 client ID (public, also used by frontend JS SDK)
#   PAYPAL_CLIENT_SECRET  – OAuth2 client secret (never sent to browser)
#   PAYPAL_BASE_URL       – https://api-m.sandbox.paypal.com  (sandbox)
#                           https://api-m.paypal.com          (live)
#   PAYPAL_PLAN_ID_STARTER – PayPal billing plan ID for the Starter plan
#   PAYPAL_PLAN_ID_PRO     – PayPal billing plan ID for the Pro plan
#   PAYPAL_WEBHOOK_ID      – webhook ID for signature verification (optional)
#
class PaypalService
  BASE_URL      = ENV.fetch("PAYPAL_BASE_URL",      "https://api-m.sandbox.paypal.com")
  CLIENT_ID     = ENV.fetch("PAYPAL_CLIENT_ID",     "")
  CLIENT_SECRET = ENV.fetch("PAYPAL_CLIENT_SECRET", "")
  WEBHOOK_ID    = ENV.fetch("PAYPAL_WEBHOOK_ID",    "")

  PLAN_IDS = {
    "starter" => ENV.fetch("PAYPAL_PLAN_ID_STARTER", ""),
    "pro"     => ENV.fetch("PAYPAL_PLAN_ID_PRO",     ""),
  }.freeze

  # Maps a PayPal plan_id back to our plan slug.
  PLAN_BY_PAYPAL_ID = PLAN_IDS.invert.freeze

  # ── OAuth2 ──────────────────────────────────────────────────────────────────

  def self.access_token
    conn = Faraday.new(BASE_URL)
    resp = conn.post("/v1/oauth2/token") do |req|
      req.headers["Accept"]          = "application/json"
      req.headers["Accept-Language"] = "en_US"
      req.headers["Content-Type"]    = "application/x-www-form-urlencoded"
      req.basic_auth(CLIENT_ID, CLIENT_SECRET)
      req.body = "grant_type=client_credentials"
    end
    body = JSON.parse(resp.body)
    raise "PayPal OAuth failed: #{body['error_description']}" unless resp.status == 200

    body["access_token"]
  end

  # ── Subscriptions ────────────────────────────────────────────────────────────

  # Returns the full PayPal subscription object for the given ID.
  def self.get_subscription(subscription_id)
    conn = Faraday.new(BASE_URL)
    resp = conn.get("/v1/billing/subscriptions/#{subscription_id}") do |req|
      req.headers["Authorization"] = "Bearer #{access_token}"
      req.headers["Content-Type"]  = "application/json"
    end
    raise "PayPal subscription fetch failed (#{resp.status})" unless resp.status == 200

    JSON.parse(resp.body)
  end

  # Cancels a subscription. reason is shown to the subscriber.
  def self.cancel_subscription(subscription_id, reason: "Cancelled by user")
    conn = Faraday.new(BASE_URL)
    resp = conn.post("/v1/billing/subscriptions/#{subscription_id}/cancel") do |req|
      req.headers["Authorization"] = "Bearer #{access_token}"
      req.headers["Content-Type"]  = "application/json"
      req.body = JSON.generate({ reason: reason })
    end
    # 204 No Content on success
    resp.status == 204
  end

  # Verifies a PayPal webhook signature.
  # headers must include the PayPal-Transmission-* headers from the inbound request.
  def self.verify_webhook(transmission_id:, transmission_time:, cert_url:,
                          transmission_sig:, webhook_event:)
    return true if WEBHOOK_ID.blank?

    conn = Faraday.new(BASE_URL)
    resp = conn.post("/v1/notifications/verify-webhook-signature") do |req|
      req.headers["Authorization"] = "Bearer #{access_token}"
      req.headers["Content-Type"]  = "application/json"
      req.body = JSON.generate({
        transmission_id:   transmission_id,
        transmission_time: transmission_time,
        cert_url:          cert_url,
        auth_algo:         "SHA256withRSA",
        transmission_sig:  transmission_sig,
        webhook_id:        WEBHOOK_ID,
        webhook_event:     webhook_event,
      })
    end
    data = JSON.parse(resp.body)
    data["verification_status"] == "SUCCESS"
  end

  # Returns plan IDs safe to expose to the frontend (no secrets).
  def self.public_plan_ids
    PLAN_IDS.reject { |_, v| v.blank? }
  end

  # Given a PayPal plan_id string, returns our internal plan slug (e.g. "pro").
  def self.plan_for(paypal_plan_id)
    PLAN_BY_PAYPAL_ID[paypal_plan_id]
  end
end
