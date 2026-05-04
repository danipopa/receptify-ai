module Api
  module V1
    class AuthController < ApplicationController
      def register
        tenant = Tenant.new(tenant_params)
        tenant.save!
        token = JsonWebToken.encode(tenant_id: tenant.id)
        render json: { token: token, tenant: tenant_json(tenant) }, status: :created
      end

      def login
        tenant = Tenant.find_by!(email: params[:email])
        raise AuthenticationError, "Invalid email or password" unless tenant.authenticate(params[:password])
        raise AuthenticationError, "Account is #{tenant.status}" unless tenant.status == "active"

        token = JsonWebToken.encode(tenant_id: tenant.id)
        render json: { token: token, tenant: tenant_json(tenant) }
      end

      private

      def tenant_params
        params.permit(:name, :subdomain, :email, :password, :password_confirmation, :plan)
      end

      def tenant_json(tenant)
        tenant.as_json(only: %i[id name subdomain email plan status created_at])
      end
    end
  end
end
