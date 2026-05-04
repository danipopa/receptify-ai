module Api
  module V1
    class BillingController < ApplicationController
      include Authenticatable

      # Webhook is called by PayPal — no JWT required.
      skip_before_action :authenticate_tenant!, only: [:webhook]

      # GET /api/v1/billing
      # Returns current subscription state + PayPal plan IDs for the JS SDK.
      def show
        render json: {
          plan:                  current_tenant.plan,
          subscription_id:       current_tenant.paypal_subscription_id,
          subscription_status:   current_tenant.subscription_status,
          plan_expires_at:       current_tenant.plan_expires_at,
          paypal_plan_ids:       PaypalService.public_plan_ids,
        }
      end

      # POST /api/v1/billing/confirm
      # Called by the frontend after PayPal JS SDK onApprove fires.
      # Body: { subscription_id: "I-XXXXXXXXXX" }
      def confirm
        subscription_id = params[:subscription_id].to_s.strip
        return render json: { error: "subscription_id is required" }, status: :unprocessable_entity if subscription_id.blank?

        begin
          sub = PaypalService.get_subscription(subscription_id)
        rescue => e
          return render json: { error: "PayPal verification failed: #{e.message}" }, status: :bad_gateway
        end

        # Require the subscription to be in an active/approved state.
        unless %w[ACTIVE APPROVED].include?(sub["status"])
          return render json: { error: "Subscription is not active (status: #{sub['status']})" }, status: :unprocessable_entity
        end

        plan_slug = PaypalService.plan_for(sub.dig("plan_id")) || "pro"

        current_tenant.update!(
          plan:                  plan_slug,
          paypal_subscription_id: subscription_id,
          subscription_status:   sub["status"].downcase,
          plan_expires_at:       nil, # Managed by PayPal recurring billing
        )

        render json: {
          plan:               current_tenant.plan,
          subscription_id:    current_tenant.paypal_subscription_id,
          subscription_status: current_tenant.subscription_status,
        }
      end

      # DELETE /api/v1/billing
      # Cancels the active PayPal subscription and downgrades to free.
      def cancel
        sub_id = current_tenant.paypal_subscription_id
        return render json: { error: "No active subscription" }, status: :unprocessable_entity if sub_id.blank?

        begin
          PaypalService.cancel_subscription(sub_id, reason: "Cancelled via Receptify dashboard")
        rescue => e
          return render json: { error: "PayPal cancellation failed: #{e.message}" }, status: :bad_gateway
        end

        current_tenant.update!(
          plan:                  "free",
          subscription_status:   "cancelled",
          plan_expires_at:       Time.current.end_of_month,
        )

        render json: {
          plan:               current_tenant.plan,
          subscription_status: current_tenant.subscription_status,
          plan_expires_at:    current_tenant.plan_expires_at,
        }
      end

      # POST /api/v1/billing/webhook
      # Receives PayPal subscription lifecycle events.
      # No JWT auth — verified by PayPal signature headers.
      def webhook
        body = request.raw_post

        # Verify webhook signature if PAYPAL_WEBHOOK_ID is configured.
        unless verify_paypal_webhook(body)
          return render json: { error: "Invalid webhook signature" }, status: :unauthorized
        end

        event = JSON.parse(body) rescue {}
        handle_webhook_event(event)

        head :no_content
      end

      private

      def verify_paypal_webhook(body)
        return true if PaypalService::WEBHOOK_ID.blank?

        PaypalService.verify_webhook(
          transmission_id:   request.headers["PayPal-Transmission-Id"],
          transmission_time: request.headers["PayPal-Transmission-Time"],
          cert_url:          request.headers["PayPal-Cert-Url"],
          transmission_sig:  request.headers["PayPal-Transmission-Sig"],
          webhook_event:     JSON.parse(body),
        )
      rescue
        false
      end

      def handle_webhook_event(event)
        event_type    = event["event_type"]
        resource      = event["resource"] || {}
        subscription_id = resource["id"]

        return unless subscription_id.present?

        tenant = Tenant.find_by(paypal_subscription_id: subscription_id)
        return unless tenant

        case event_type
        when "BILLING.SUBSCRIPTION.ACTIVATED"
          plan_slug = PaypalService.plan_for(resource["plan_id"]) || "pro"
          tenant.update!(plan: plan_slug, subscription_status: "active")

        when "BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.EXPIRED",
             "BILLING.SUBSCRIPTION.SUSPENDED"
          tenant.update!(
            plan:               "free",
            subscription_status: event_type.split(".").last.downcase,
            plan_expires_at:    Time.current.end_of_month,
          )

        when "BILLING.SUBSCRIPTION.UPDATED"
          new_plan = PaypalService.plan_for(resource.dig("plan_overridden", "plan_id"))
          tenant.update!(plan: new_plan) if new_plan.present?
        end
      end
    end
  end
end
