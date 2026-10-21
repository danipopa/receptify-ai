module Api
  module V1
    class AvailabilityRulesController < BaseController
      def index
        render json: { availability_rules: workspace.availability_rules.order(:day_of_week, :start_time) }
      end

      def create
        rule = workspace.availability_rules.create!(rule_params)
        render json: { availability_rule: rule }, status: :created
      end

      def update
        rule = workspace.availability_rules.find(params[:id])
        rule.update!(rule_params)
        render json: { availability_rule: rule }
      end

      def destroy
        workspace.availability_rules.find(params[:id]).destroy!
        head :no_content
      end

      private

      def workspace
        @workspace ||= current_tenant.client_workspaces.find(params[:client_workspace_id])
      end

      def rule_params
        params.permit(:day_of_week, :start_time, :end_time)
      end
    end
  end
end
