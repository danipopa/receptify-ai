module Api
  module V1
    class DidsController < BaseController
      DID_ATTRS = %i[
        id number provider status
        gateway_type gateway_host gateway_user gateway_realm gateway_port
        created_at
      ].freeze

      def index
        page  = (params[:page] || 1).to_i
        limit = PAGINATION_DEFAULT_LIMIT
        dids  = current_tenant.dids.order(created_at: :desc)
                              .offset((page - 1) * limit).limit(limit)
        render json: {
          dids: dids.as_json(only: DID_ATTRS),
          meta: { page: page, limit: limit, total: current_tenant.dids.count }
        }
      end

      def create
        did = current_tenant.dids.create!(did_params)
        render json: did.as_json(only: DID_ATTRS), status: :created
      end

      def update
        did = current_tenant.dids.find(params[:id])
        did.update!(did_params)
        render json: did.as_json(only: DID_ATTRS)
      end

      def destroy
        did = current_tenant.dids.find(params[:id])
        did.destroy!
        head :no_content
      end

      private

      def did_params
        params.permit(
          :number, :provider, :status,
          :gateway_type, :gateway_host, :gateway_user,
          :gateway_password, :gateway_realm, :gateway_port
        )
      end
    end
  end
end
