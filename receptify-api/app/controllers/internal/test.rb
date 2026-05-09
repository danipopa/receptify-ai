module Internal
  class FreeswitchController < ActionController::API
    # mod_xml_curl does NOT send an auth header — it's internal-network only.
    # We skip token auth for these endpoints (they're not exposed via ingress).
    skip_before_action :verify_authenticity_token, raise: false

    FS_DOMAIN = ENV.fetch("FS_DOMAIN", "receptify.local")

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
      when "configuration"
        render_configuration
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
      dest = (params[:destination_number] ||
              params["Caller-Destination-Number"] ||
              params["Hunt-Destination-Number"]).to_s.gsub(/\A\+/, "")
      did  = Did.find_by(number: "+#{dest}") ||
             Did.find_by(number: dest) ||
             Did.find_by(gateway_user: dest)

      unless did&.status == "active"
        return render_not_found
      end

      number = did.number

      xml = <<~XML
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <document type="freeswitch/xml">
          <section name="dialplan">
            <context name="public">
              <extension name="inbound-#{did.fs_gateway_name}">
                <condition field="destination_number" expression="^\\+?#{dest}$">
                  <action application="set" data="call_did=#{number}"/>
                  <action application="answer"/>
                  <action application="park"/>
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

    def render_configuration
      # FreeSWITCH requests configuration sections via xml_curl on startup and on
      # "sofia profile external rescan".  We only handle sofia.conf — all other
      # sections get a not-found so FreeSWITCH falls back to its static files.
      unless params[:key_value] == "sofia.conf"
        return render_not_found
      end

      ext_ip  = ENV.fetch("FS_EXT_SIP_IP", "auto-nat")

      gateways = Did.where(gateway_type: "sip_registration", status: "active")

      gateway_xml = gateways.map do |did|
        realm = did.gateway_realm
        port  = did.gateway_port || 5060
        <<~GATEWAY
          <gateway name="#{did.fs_gateway_name}">
            <param name="username"            value="#{did.gateway_user}"/>
            <param name="password"            value="#{did.gateway_password}"/>
            <param name="proxy"               value="#{did.gateway_host}:#{port}"/>
            <param name="realm"               value="#{realm}"/>
            <param name="register"            value="true"/>
            <param name="from-user"           value="#{did.gateway_user}"/>
            <param name="from-domain"         value="#{did.gateway_host}"/>
            <param name="caller-id-in-from"   value="false"/>
            <param name="context"             value="public"/>
          </gateway>
        GATEWAY
      end.join
      logger.debug "Generating sofia.conf with #{gateways.count} gateways:\n#{gateway_xml}"
      xml = <<~XML
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <document type="freeswitch/xml">
          <section name="configuration">
            <configuration name="sofia.conf" description="Sofia SIP">
              <global_settings>
                <param name="log-level" value="0"/>
                <param name="debug-presence" value="0"/>
              </global_settings>
              <profiles>
                <profile name="internal">
                  <gateways/>
                  <aliases/>
                  <domains>
                    <domain name="all" alias="true" parse="false"/>
                  </domains>
                  <settings>
                    <param name="debug"                           value="0"/>
                    <param name="sip-trace"                       value="no"/>
                    <param name="rfc2833-pt"                      value="101"/>
                    <param name="sip-port"                        value="5060"/>
                    <param name="dialplan"                        value="XML"/>
                    <param name="context"                         value="public"/>
                    <param name="dtmf-duration"                   value="2000"/>
                    <param name="inbound-codec-prefs"             value="OPUS,G722,PCMU,PCMA"/>
                    <param name="outbound-codec-prefs"            value="OPUS,G722,PCMU,PCMA"/>
                    <param name="inbound-codec-negotiation"       value="generous"/>
                    <param name="rtp-ip"                          value="0.0.0.0"/>
                    <param name="sip-ip"                          value="0.0.0.0"/>
                    <param name="ext-rtp-ip"                      value="#{ext_ip}"/>
                    <param name="ext-sip-ip"                      value="#{ext_ip}"/>
                    <param name="rtp-timer-name"                  value="soft"/>
                    <param name="hold-music"                      value="local_stream://moh"/>
                    <param name="manage-presence"                 value="false"/>
                    <param name="aggressive-nat-detection"        value="true"/>
                    <param name="enable-timer"                    value="false"/>
                    <param name="rtp-timeout-sec"                 value="300"/>
                    <param name="rtp-hold-timeout-sec"            value="1800"/>
                    <param name="auth-calls"                      value="false"/>
                    <param name="nonce-ttl"                       value="60"/>
                  </settings>
                </profile>
                <profile name="external">
                  <gateways>
                    #{gateway_xml.indent(20).lstrip}
                  </gateways>
                  <aliases/>
                  <domains/>
                  <settings>
                    <param name="debug"                           value="0"/>
                    <param name="sip-trace"                       value="no"/>
                    <param name="rfc2833-pt"                      value="101"/>
                    <param name="sip-port"                        value="5080"/>
                    <param name="dialplan"                        value="XML"/>
                    <param name="context"                         value="public"/>
                    <param name="dtmf-duration"                   value="2000"/>
                    <param name="inbound-codec-prefs"             value="OPUS,G722,PCMU,PCMA"/>
                    <param name="outbound-codec-prefs"            value="OPUS,G722,PCMU,PCMA"/>
                    <param name="inbound-codec-negotiation"       value="generous"/>
                    <param name="rtp-ip"                          value="0.0.0.0"/>
                    <param name="sip-ip"                          value="0.0.0.0"/>
                    <param name="ext-rtp-ip"                      value="#{ext_ip}"/>
                    <param name="ext-sip-ip"                      value="#{ext_ip}"/>
                    <param name="rtp-timer-name"                  value="soft"/>
                    <param name="hold-music"                      value="local_stream://moh"/>
                    <param name="local-network-acl"               value="localnet.auto"/>
                    <param name="manage-presence"                 value="false"/>
                    <param name="enable-timer"                    value="false"/>
                    <param name="auth-calls"                      value="false"/>
                    <param name="inbound-late-negotiation"        value="true"/>
                    <param name="nonce-ttl"                       value="60"/>
                    <param name="rtp-timeout-sec"                 value="300"/>
                    <param name="rtp-hold-timeout-sec"            value="1800"/>
                  </settings>
                </profile>
              </profiles>
            </configuration>
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
      did = Did.find_by(number: number) ||
            Did.find_by(number: dest) ||
            Did.find_by(gateway_user: dest)
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
