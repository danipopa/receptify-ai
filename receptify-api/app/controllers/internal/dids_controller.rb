module Internal
  class DidsController < ActionController::API
    before_action :authenticate_internal!
    before_action :load_did

    # GET /internal/dids/:number/config
    # Called by the agent on each incoming call to get per-DID tenant config.
    def config
      cfg = @did.tenant.tenant_config || TenantConfig.new(TenantConfig.column_defaults)
      render json: {
        did:             @did.number,
        tenant_id:       @did.tenant_id,
        gateway_type:    @did.gateway_type,
        welcome_message: cfg.welcome_message,
        voice:           cfg.voice,
        llm_model:       cfg.llm_model,
        rag_top_k:       cfg.rag_top_k,
        rag_chunk_words: cfg.rag_chunk_words,
        timezone:        cfg.timezone,
      }
    end

    # GET /internal/dids/:number/fs_gateway
    # Returns FreeSWITCH XML for a sip_registration gateway.
    # Drop into /usr/local/freeswitch/conf/sip_profiles/external/
    def fs_gateway
      unless @did.gateway_type == "sip_registration"
        return render json: { error: "DID gateway_type is not sip_registration" }, status: :unprocessable_entity
      end

      xml = <<~XML
        <include>
          <gateway name="#{@did.fs_gateway_name}">
            <param name="username"  value="#{@did.gateway_user}"/>
            <param name="password"  value="#{@did.gateway_password}"/>
            <param name="proxy"     value="#{@did.gateway_host}:#{@did.gateway_port || 5060}"/>
            #{@did.gateway_realm.present? ? "<param name=\"realm\" value=\"#{@did.gateway_realm}\"/>" : ''}
            <param name="register"  value="true"/>
            <param name="context"   value="public"/>
            <param name="caller-id-in-from" value="true"/>
          </gateway>
        </include>
      XML

      render plain: xml, content_type: "application/xml"
    end

    # GET /internal/dids/:number/fs_dialplan
    # Returns FreeSWITCH dialplan XML fragment for routing this DID to the agent.
    # Append to /usr/local/freeswitch/conf/dialplan/public/
    def fs_dialplan
      agent_url = ENV.fetch("AGENT_WS_URL", "ws://agent:9090")
      number_e164 = @did.number.gsub(/\D/, "")

      xml = <<~XML
        <include>
          <extension name="inbound-#{@did.fs_gateway_name}">
            <condition field="destination_number" expression="^\\+?#{number_e164}$">
              <action application="answer"/>
              <action application="uuid_audio_stream"
                      data="#{agent_url}/ws/${uuid}?did=#{@did.number} mono 48000"/>
              <action application="sleep" data="3600000"/>
            </condition>
          </extension>
        </include>
      XML

      render plain: xml, content_type: "application/xml"
    end

    private

    def authenticate_internal!
      token = ENV.fetch("INTERNAL_TOKEN", nil)&.strip
      return if token.blank?
      unless request.headers["X-Internal-Token"].to_s.strip == token
        head :unauthorized
      end
    end

    def load_did
      @did = Did.find_by!(number: params[:number])
    rescue ActiveRecord::RecordNotFound
      render json: { error: "DID not found" }, status: :not_found
    end
  end
end
