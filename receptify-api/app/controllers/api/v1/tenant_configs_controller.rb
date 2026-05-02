module Api
  module V1
    class TenantConfigsController < BaseController
      def show
        render json: current_tenant.tenant_config
      end

      def update
        current_tenant.tenant_config.update!(config_params)
        render json: current_tenant.tenant_config
      end

      private

      def config_params
        params.permit(:welcome_message, :llm_model, :rag_chunk_words, :rag_top_k, :voice, :timezone)
      end
    end
  end
end
