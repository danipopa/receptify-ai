module Api
  module V1
    class AppointmentTypesController < BaseController
      def index
        render json: { appointment_types: workspace.appointment_types.order(:name) }
      end

      def create
        appointment_type = workspace.appointment_types.create!(appointment_type_params)
        render json: { appointment_type: appointment_type }, status: :created
      end

      def update
        appointment_type = workspace.appointment_types.find(params[:id])
        appointment_type.update!(appointment_type_params)
        render json: { appointment_type: appointment_type }
      end

      def destroy
        appointment_type = workspace.appointment_types.find(params[:id])
        if appointment_type.appointments.exists?
          return render json: { error: "Appointment types with existing bookings cannot be removed" },
                        status: :unprocessable_entity
        end

        appointment_type.destroy!
        head :no_content
      end

      private

      def workspace
        @workspace ||= current_tenant.client_workspaces.find(params[:client_workspace_id])
      end

      def appointment_type_params
        params.permit(:name, :duration_minutes, :active)
      end
    end
  end
end
