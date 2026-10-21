module Api
  module V1
    class AvailabilityExceptionsController < BaseController
      def index
        render json: { availability_exceptions: workspace.availability_exceptions.order(:date, :start_time) }
      end

      def create
        exception = workspace.availability_exceptions.create!(exception_params)
        render json: { availability_exception: exception }, status: :created
      end

      def update
        exception = workspace.availability_exceptions.find(params[:id])
        exception.update!(exception_params)
        render json: { availability_exception: exception }
      end

      def destroy
        workspace.availability_exceptions.find(params[:id]).destroy!
        head :no_content
      end

      private

      def workspace
        @workspace ||= current_tenant.client_workspaces.find(params[:client_workspace_id])
      end

      def exception_params
        params.permit(:date, :all_day, :start_time, :end_time, :description)
      end
    end
  end
end
