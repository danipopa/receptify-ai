module Api
  module V1
    class AdminController < BaseController
      before_action :require_platform_admin!

      def overview
        customers = Tenant.where(platform_admin: false)
        customer_ids = customers.select(:id)
        dids = Did.where(tenant_id: customer_ids)
        calls = CallLog.where(tenant_id: customer_ids)
        workspaces = ClientWorkspace.where(tenant_id: customer_ids)
        appointments = Appointment.where(client_workspace_id: workspaces.select(:id))

        did_counts = dids.group(:tenant_id).count
        call_counts = calls.group(:tenant_id).count

        render json: {
          metrics: {
            customer_count: customers.count,
            active_customer_count: customers.where(status: "active").count,
            paid_customer_count: customers.where(plan: %w[starter pro enterprise]).count,
            did_count: dids.count,
            active_did_count: dids.where(status: "active").count,
            call_count: calls.count,
            calls_today: calls.where(started_at: Time.current.all_day).count,
            upcoming_appointments: appointments.where(status: "confirmed", starts_at: Time.current..).count
          },
          customers: customers.order(created_at: :desc).map do |customer|
            {
              id: customer.id,
              name: customer.name,
              email: customer.email,
              subdomain: customer.subdomain,
              plan: customer.plan,
              status: customer.status,
              subscription_status: customer.subscription_status,
              plan_expires_at: customer.plan_expires_at,
              created_at: customer.created_at,
              did_count: did_counts.fetch(customer.id, 0),
              call_count: call_counts.fetch(customer.id, 0)
            }
          end,
          dids: dids.includes(:tenant, :client_workspace).order(created_at: :desc).map do |did|
            {
              id: did.id,
              number: did.number,
              provider: did.provider,
              status: did.status,
              gateway_type: did.gateway_type,
              created_at: did.created_at,
              customer_name: did.tenant.name,
              customer_email: did.tenant.email,
              client_workspace_name: did.client_workspace&.name
            }
          end,
          recent_activity: recent_activity(customer_ids)
        }
      end

      private

      def require_platform_admin!
        return if current_tenant.platform_admin?

        render json: { error: "Platform administrator access required" }, status: :forbidden
      end

      def recent_activity(customer_ids)
        call_activity = CallLog.includes(:tenant, :did)
          .where(tenant_id: customer_ids)
          .order(started_at: :desc)
          .limit(50)
          .map do |call|
            {
              id: "call-#{call.id}",
              type: "call",
              occurred_at: call.started_at,
              customer_name: call.tenant.name,
              detail: "#{call.direction.titleize} call from #{call.caller_number}",
              reference: call.did&.number
            }
          end

        appointment_activity = Appointment.includes(:appointment_type, client_workspace: :tenant)
          .joins(:client_workspace)
          .where(client_workspaces: { tenant_id: customer_ids })
          .order(created_at: :desc)
          .limit(50)
          .map do |appointment|
            {
              id: "appointment-#{appointment.id}",
              type: "appointment",
              occurred_at: appointment.created_at,
              customer_name: appointment.client_workspace.tenant.name,
              detail: "#{appointment.status.titleize} appointment for #{appointment.caller_name}",
              reference: appointment.client_workspace.name
            }
          end

        (call_activity + appointment_activity)
          .sort_by { |event| event[:occurred_at] }
          .reverse
          .first(100)
      end
    end
  end
end
