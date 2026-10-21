module Api
  module V1
    class ClientWorkspacesController < BaseController
      STARTER_WORKSPACES = [
        {
          name: "Mobiletel",
          website_url: "https://mobiletel.eu",
          locale: "en-GB",
          appointment_type: "General consultation",
          knowledge_source: "https://mobiletel.eu",
          knowledge_content: <<~CONTENT
            Draft based on the public website at https://mobiletel.eu.
            The available public-page summary describes Mobiletel as providing comprehensive technology solutions.
            The available information does not specify particular products or services, pricing, opening hours, service locations, or appointment requirements.
            Confirm these details with Mobiletel before relying on them to answer callers.
          CONTENT
        },
        {
          name: "inregistrare-marca.com",
          website_url: "https://inregistrare-marca.com",
          locale: "ro-RO",
          appointment_type: "Trademark consultation",
          knowledge_source: "https://inregistrare-marca.com",
          knowledge_content: <<~CONTENT
            Draft based on the public website at https://inregistrare-marca.com.
            The available public-page summary describes trademark monitoring for OSIM, EUIPO, and WIPO. The service detects identical or similar marks, provides strategic and legal response suggestions, and sends monthly email reports.
            The available information does not specify prices, appointment availability, opening hours, or guaranteed legal outcomes.
            Confirm service details with the client before relying on them to answer callers.
          CONTENT
        }
      ].freeze

      def index
        render json: { client_workspaces: current_tenant.client_workspaces.order(:name).map { |workspace| workspace_json(workspace) } }
      end

      def show
        render json: { client_workspace: workspace_json(load_workspace, include_content: true) }
      end

      def create
        workspace = current_tenant.client_workspaces.create!(workspace_params)
        render json: { client_workspace: workspace_json(workspace, include_content: true) }, status: :created
      end

      def update
        workspace = load_workspace
        workspace.update!(workspace_params)
        render json: { client_workspace: workspace_json(workspace, include_content: true) }
      end

      def knowledge
        workspace = load_workspace
        status = params[:knowledge_status].presence || "draft"
        workspace.update!(
          knowledge_content: params.require(:knowledge_content),
          knowledge_source: params[:knowledge_source],
          knowledge_status: status
        )
        render json: { client_workspace: workspace_json(workspace, include_content: true) }
      end

      def seed_starters
        workspaces = STARTER_WORKSPACES.map do |attributes|
          current_tenant.client_workspaces.find_or_create_by!(website_url: attributes.fetch(:website_url)) do |workspace|
            workspace.name = attributes.fetch(:name)
            workspace.locale = attributes.fetch(:locale)
            workspace.timezone = "UTC"
            workspace.knowledge_source = attributes.fetch(:knowledge_source)
            workspace.knowledge_content = attributes.fetch(:knowledge_content)
            workspace.knowledge_status = "draft"
          end.tap do |workspace|
            workspace.appointment_types.find_or_create_by!(name: attributes.fetch(:appointment_type)) do |appointment_type|
              appointment_type.duration_minutes = 30
            end
          end
        end

        render json: { client_workspaces: workspaces.map { |workspace| workspace_json(workspace, include_content: true) } }, status: :created
      end

      def availability
        workspace = load_workspace
        appointment_type = workspace.appointment_types.find_by!(id: params.require(:appointment_type_id), active: true)
        from = Date.iso8601(params.require(:from))
        to = Date.iso8601(params.require(:to))
        limit = params.fetch(:limit, 20).to_i
        slots = AvailabilityService.new(client_workspace: workspace, appointment_type: appointment_type)
                                   .slots(from: from, to: to, limit: limit)
        render json: { slots: slots, timezone: workspace.timezone }
      rescue ArgumentError => e
        render json: { error: e.message }, status: :bad_request
      end

      private

      def load_workspace
        current_tenant.client_workspaces.find(params[:id] || params[:client_workspace_id])
      end

      def workspace_params
        params.permit(:name, :website_url, :timezone, :locale)
      end

      def workspace_json(workspace, include_content: false)
        attributes = %i[id name website_url timezone locale knowledge_source knowledge_status created_at]
        attributes << :knowledge_content if include_content
        payload = workspace.as_json(only: attributes).merge(
          appointment_types: workspace.appointment_types.order(:name).as_json(only: %i[id name duration_minutes active]),
          availability_rules: workspace.availability_rules.order(:day_of_week, :start_time).as_json(only: %i[id day_of_week start_time end_time]),
          availability_exceptions: workspace.availability_exceptions.order(:date, :start_time).as_json(only: %i[id date all_day start_time end_time description]),
          number_requests: workspace.mock_number_requests.order(created_at: :desc).as_json(only: %i[id country_code country_name locale number simulated created_at])
        )
        if include_content
          payload[:appointments] = workspace.appointments.includes(:appointment_type)
                                            .order(starts_at: :desc).limit(100).map do |appointment|
            appointment.as_json(only: %i[id appointment_type_id caller_name callback_number purpose starts_at ends_at status])
                       .merge(appointment_type_name: appointment.appointment_type.name)
          end
        end
        payload
      end
    end
  end
end
