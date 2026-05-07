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
        sync_gateway(did)
        render json: did.as_json(only: DID_ATTRS), status: :created
      end

      def update
        did = current_tenant.dids.find(params[:id])
        old_type = did.gateway_type
        did.update!(did_params)
        # Remove old gateway file if type changed away from sip_registration
        delete_gateway(did) if old_type == "sip_registration" && did.gateway_type != "sip_registration"
        sync_gateway(did)
        render json: did.as_json(only: DID_ATTRS)
      end

      def destroy
        did = current_tenant.dids.find(params[:id])
        delete_gateway(did)
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

      # Trigger FreeSWITCH to re-fetch sofia.conf from xml_curl (picks up new/removed gateways).
      # Only needed for sip_registration type (FS registers outbound to provider).
      def sync_gateway(did)
        return unless did.gateway_type == "sip_registration"

        fs_bridge_url = ENV.fetch("FS_BRIDGE_URL", nil)
        return if fs_bridge_url.blank?

        conn = Faraday.new(url: fs_bridge_url) { |f| f.adapter :net_http }
        resp = conn.post("/sync/reload", "{}", "Content-Type" => "application/json")
        Rails.logger.warn "fs-bridge reload failed: #{resp.status}" unless resp.success?
      rescue => e
        Rails.logger.warn "fs-bridge reload error: #{e.message}"
      end

      def delete_gateway(did)
        return unless did.gateway_type == "sip_registration"

        fs_bridge_url = ENV.fetch("FS_BRIDGE_URL", nil)
        return if fs_bridge_url.blank?

        conn = Faraday.new(url: fs_bridge_url) { |f| f.adapter :net_http }
        resp = conn.post("/sync/reload", "{}", "Content-Type" => "application/json")
        Rails.logger.warn "fs-bridge reload failed: #{resp.status}" unless resp.success?
      rescue => e
        Rails.logger.warn "fs-bridge gateway delete error: #{e.message}"
      end
    end
  end
end
