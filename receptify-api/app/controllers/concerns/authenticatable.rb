module Authenticatable
  extend ActiveSupport::Concern

  included do
    before_action :authenticate_tenant!
  end

  private

  def authenticate_tenant!
    token = extract_token
    raise AuthenticationError, "Missing token" unless token

    payload = JsonWebToken.decode(token)
    @current_tenant = Tenant.find_by(id: payload[:tenant_id], status: "active")
    raise AuthenticationError, "Tenant not found or inactive" unless @current_tenant
  end

  def current_tenant
    @current_tenant
  end

  def extract_token
    header = request.headers["Authorization"]
    header&.split(" ")&.last
  end
end
