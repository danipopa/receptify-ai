module Internal
  class ClientWorkspacesController < ActionController::API
    before_action :authenticate_internal!
    before_action :load_workspace

    def knowledge
      render json: {
        workspace_id: @workspace.id,
        content: @workspace.knowledge_status == "ready" ? @workspace.knowledge_content : "",
        knowledge_status: @workspace.knowledge_status,
        updated_at: @workspace.updated_at.iso8601
      }
    end

    def appointment_types
      render json: {
        workspace_id: @workspace.id,
        timezone: @workspace.timezone,
        locale: @workspace.locale,
        appointment_types: @workspace.appointment_types.where(active: true).order(:name).as_json(only: %i[id name duration_minutes])
      }
    end

    def availability
      appointment_type = @workspace.appointment_types.find_by!(id: params.require(:appointment_type_id), active: true)
      from = Date.iso8601(params.require(:from))
      to = Date.iso8601(params.require(:to))
      slots = AvailabilityService.new(client_workspace: @workspace, appointment_type: appointment_type)
                                 .slots(from: from, to: to, limit: params.fetch(:limit, 20))
      render json: { slots: slots, timezone: @workspace.timezone }
    rescue ArgumentError => e
      render json: { error: e.message }, status: :bad_request
    end

    def appointments
      unless ActiveModel::Type::Boolean.new.cast(params[:confirmed])
        return render json: { error: "Caller confirmation is required before booking" }, status: :unprocessable_entity
      end

      appointment_type = @workspace.appointment_types.find_by!(id: params.require(:appointment_type_id), active: true)
      appointment = AppointmentBookingService.new(
        client_workspace: @workspace,
        appointment_type: appointment_type
      ).call(
        caller_name: params.require(:caller_name),
        callback_number: params.require(:callback_number),
        starts_at: params.require(:starts_at),
        purpose: params[:purpose]
      )
      render json: {
        appointment: appointment.as_json(only: %i[id appointment_type_id caller_name callback_number purpose starts_at ends_at status]),
        timezone: @workspace.timezone
      }, status: :created
    rescue AppointmentBookingService::SlotUnavailable => e
      render json: { error: e.message }, status: :conflict
    rescue ArgumentError => e
      render json: { error: e.message }, status: :bad_request
    end

    private

    def authenticate_internal!
      token = ENV.fetch("INTERNAL_TOKEN", nil)&.strip
      return if token.blank?
      supplied = request.headers["X-Internal-Token"].to_s.strip
      return if supplied.bytesize == token.bytesize &&
                ActiveSupport::SecurityUtils.secure_compare(supplied, token)

      head :unauthorized
    end

    def load_workspace
      @workspace = ClientWorkspace.find(params[:id])
    rescue ActiveRecord::RecordNotFound
      render json: { error: "Client workspace not found" }, status: :not_found
    end
  end
end
