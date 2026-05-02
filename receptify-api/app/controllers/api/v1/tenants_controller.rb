module Api
  module V1
    class TenantsController < BaseController
      def show
        render json: current_tenant.as_json(
          only: %i[id name subdomain email plan status api_key created_at],
          include: { tenant_config: { except: %i[tenant_id created_at updated_at] } }
        )
      end

      def update
        current_tenant.update!(tenant_update_params)
        render json: current_tenant.as_json(only: %i[id name subdomain email plan status])
      end

      private

      def tenant_update_params
        params.permit(:name, :email)
      end
    end
  end
end
