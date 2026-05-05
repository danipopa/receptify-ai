module Internal
  class FreeswitchController < ActionController::API
    # mod_xml_curl does NOT send an auth header — it's internal-network only.
    # We skip token auth for these endpoints (they're not exposed via ingress).
    skip_before_action :verify_authenticity_token, raise: false

    AGENT_WS_URL = ENV.fetch("AGENT_WS_URL", "ws://agent:9090")
    FS_DOMAIN    = ENV.fetch("FS_DOMAIN", "receptify.local")

    # POST /internal/freeswitch/xml
    # Called by mod_xml_curl with form params:
    #   section=dialplan|directory  key_value=destination_number|username  etc.
    def xml
      section = params[:section]

      case section
      when "dialplan"
        render_dialplan
      when "directory"
        render_directory
      else
        render_not_found
      end
    end

    # POST /internal/freeswitch/cdr
    # Called by mod_xml_cdr at call end with XML CDR body.
    def cdr
      body = request.raw_post
      doc  = Nokogiri::XML(body) rescue nil

      if doc
        cdr_node = doc.at("cdr") || doc.at("//cdr")
        if cdr_node
          process_cdr(cdr_node)
        end
      end

      head :ok
    end

    private

    def render_dialplan
      dest = params[:destination_number].to_s.gsub(/\A\+/, "")
      did  = Did.find_by(number: "+#{dest}") || Did.find_by(number: dest)

      unless did&.status == "active"
        return render_not_found
      end

      agent_url = AGENT_WS_URL
      number    = did.number

      xml = <<~XML
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <document type="freeswitch/xml">
          <section name="dialplan">
            <context name="public">
              <extension name="inbound-#{did.fs_gateway_name}">
                <condition field="destination_number" expression="^\\+?#{dest}$">
                  <action application="answer"/>
                  <action application="set" data="call_did=#{number}"/>
                  <action application="uuid_audio_stream"
                          data="#{agent_url}/ws/${uuid}?did=#{number} mono 48000"/>
                  <action application="sleep" data="3600000"/>
                </condition>
              </extension>
            </context>
          </section>
        </document>
      XML

      render plain: xml, content_type: "text/xml"
    end

    def render_directory
      # Called when FreeSWITCH needs to authenticate a SIP registration or lookup a user.
      # For sip_registration DIDs: user = gateway_user, domain = gateway_realm || FS_DOMAIN
      username = params[:user] || params[:key_value]
      domain   = params[:domain] || FS_DOMAIN

      did = Did.where(gateway_type: "sip_registration")
               .where(gateway_user: username)
               .first

      unless did
        return render_not_found
      end

      xml = <<~XML
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <document type="freeswitch/xml">
          <section name="directory">
            <domain name="#{domain}">
              <user id="#{did.gateway_user}">
                <params>
                  <param name="password" value="#{did.gateway_password}"/>
                </params>
                <variables>
                  <variable name="user_context" value="public"/>
                  <variable name="call_did" value="#{did.number}"/>
                </variables>
              </user>
            </domain>
          </section>
        </document>
      XML

      render plain: xml, content_type: "text/xml"
    end

    def render_not_found
      xml = <<~XML
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <document type="freeswitch/xml">
          <section name="result">
            <result status="not found"/>
          </section>
        </document>
      XML
      render plain: xml, content_type: "text/xml", status: :ok
    end

    def process_cdr(cdr)
      dest      = cdr.at("callflow/caller_profile/destination_number")&.text.to_s
      caller    = cdr.at("callflow/caller_profile/caller_id_number")&.text.to_s
      started   = cdr.at("variables/start_epoch")&.text.to_i
      ended     = cdr.at("variables/end_epoch")&.text.to_i
      duration  = cdr.at("variables/duration")&.text.to_i

      number = dest.start_with?("+") ? dest : "+#{dest}"
      did = Did.find_by(number: number) || Did.find_by(number: dest)
      return unless did

      CallLog.create!(
        tenant:        did.tenant,
        did:           did,
        caller_number: caller,
        direction:     "inbound",
        started_at:    started > 0 ? Time.at(started) : Time.current,
        ended_at:      ended   > 0 ? Time.at(ended)   : Time.current,
        duration:      duration,
      )
    rescue => e
      Rails.logger.warn "CDR processing error: #{e.message}"
    end
  end
end
