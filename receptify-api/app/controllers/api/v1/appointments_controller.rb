module Api
  module V1
    class AppointmentsController < BaseController
      def index
        appointments = workspace.appointments.includes(:appointment_type).order(:starts_at)
        render json: { appointments: appointments.map { |appointment| appointment_json(appointment) } }
      end

      def create
        appointment_type = workspace.appointment_types.find_by!(id: params.require(:appointment_type_id), active: true)
        appointment = AppointmentBookingService.new(
          client_workspace: workspace,
          appointment_type: appointment_type
        ).call(
          caller_name: params.require(:caller_name),
          callback_number: params.require(:callback_number),
          starts_at: params.require(:starts_at),
          purpose: params[:purpose]
        )
        render json: { appointment: appointment_json(appointment) }, status: :created
      rescue AppointmentBookingService::SlotUnavailable => e
        render json: { error: e.message }, status: :conflict
      rescue ArgumentError => e
        render json: { error: e.message }, status: :bad_request
      end

      def destroy
        appointment = workspace.appointments.find(params[:id])
        appointment.update!(status: "cancelled")
        render json: { appointment: appointment_json(appointment) }
      end

      private

      def workspace
        @workspace ||= current_tenant.client_workspaces.find(params[:client_workspace_id])
      end

      def appointment_json(appointment)
        appointment.as_json(only: %i[id appointment_type_id caller_name callback_number purpose starts_at ends_at status created_at])
                    .merge(appointment_type_name: appointment.appointment_type.name)
      end
    end
  end
end
