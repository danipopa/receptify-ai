#!/bin/bash
set -e

VARS_XML=/usr/local/freeswitch/conf/vars.xml
ESL_CONF=/usr/local/freeswitch/conf/autoload_configs/event_socket.conf.xml
XML_CURL_CONF=/usr/local/freeswitch/conf/autoload_configs/xml_curl.conf.xml
XML_CDR_CONF=/usr/local/freeswitch/conf/autoload_configs/xml_cdr.conf.xml

# Inject external SIP/RTP IP
if [ -n "$FS_EXT_SIP_IP" ] && [ -f "$VARS_XML" ]; then
  sed -i 's|data="ext-sip-ip=[^"]*"|data="ext-sip-ip='"${FS_EXT_SIP_IP}"'"|' "$VARS_XML"
  sed -i 's|data="ext-rtp-ip=[^"]*"|data="ext-rtp-ip='"${FS_EXT_SIP_IP}"'"|' "$VARS_XML"
fi

if [ -n "$FS_EXT_RTP_IP" ] && [ -f "$VARS_XML" ]; then
  sed -i 's|data="ext-rtp-ip=[^"]*"|data="ext-rtp-ip='"${FS_EXT_RTP_IP}"'"|' "$VARS_XML"
fi

# Write event_socket.conf.xml — allow pod network in addition to loopback
if [ -n "$FS_ESL_PASSWORD" ]; then
  mkdir -p "$(dirname "$ESL_CONF")"
  cat > "$ESL_CONF" <<EOF
<configuration name="event_socket.conf" description="Socket Client">
  <settings>
    <param name="nat-map" value="false"/>
    <param name="listen-ip" value="0.0.0.0"/>
    <param name="listen-port" value="8021"/>
    <param name="password" value="${FS_ESL_PASSWORD}"/>
    <param name="apply-inbound-acl" value="esl_acl"/>
  </settings>
</configuration>
EOF
  # Write ACL to allow loopback + pod network (172.16.0.0/12 covers 172.31.x.x)
  ACL_CONF=/usr/local/freeswitch/conf/autoload_configs/acl.conf.xml
  if [ -f "$ACL_CONF" ]; then
    # Add esl_acl list if not already present
    if ! grep -q "esl_acl" "$ACL_CONF"; then
      sed -i 's|</network-lists>|  <list name="esl_acl" default="deny">\n      <node type="allow" cidr="127.0.0.1/32"/>\n      <node type="allow" cidr="172.16.0.0/12"/>\n      <node type="allow" cidr="10.0.0.0/8"/>\n    </list>\n  </network-lists>|' "$ACL_CONF"
    fi
  fi
fi

# Write xml_curl.conf.xml if API_URL is set
if [ -n "$API_URL" ]; then
  mkdir -p "$(dirname "$XML_CURL_CONF")"
  cat > "$XML_CURL_CONF" <<EOF
<configuration name="xml_curl.conf" description="cURL XML Gateway">
  <bindings>
    <binding name="receptify-dialplan">
      <param name="gateway-url" value="${API_URL}/internal/freeswitch/xml"/>
      <param name="bindings" value="dialplan|directory"/>
    </binding>
  </bindings>
</configuration>
EOF
  echo "Wrote xml_curl.conf.xml → ${API_URL}/internal/freeswitch/xml"
fi

# Write xml_cdr.conf.xml if API_URL is set
if [ -n "$API_URL" ]; then
  mkdir -p "$(dirname "$XML_CDR_CONF")"
  cat > "$XML_CDR_CONF" <<EOF
<configuration name="xml_cdr.conf" description="XML CDR">
  <settings>
    <param name="url" value="${API_URL}/internal/freeswitch/cdr"/>
    <param name="retries" value="2"/>
    <param name="delay" value="5000"/>
    <param name="method" value="POST"/>
    <param name="encode" value="true"/>
    <param name="log-b-leg" value="false"/>
    <param name="prefix-a-leg" value="false"/>
  </settings>
</configuration>
EOF
  echo "Wrote xml_cdr.conf.xml → ${API_URL}/internal/freeswitch/cdr"
fi

exec /usr/local/freeswitch/bin/freeswitch "$@"
