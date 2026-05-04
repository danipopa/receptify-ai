#!/bin/bash
set -e

VARS_XML=/etc/freeswitch/vars.xml

# Inject external SIP/RTP IP from env vars into vars.xml
if [ -n "$FS_EXT_SIP_IP" ] && [ -f "$VARS_XML" ]; then
  sed -i 's|data="ext-sip-ip=[^"]*"|data="ext-sip-ip='"${FS_EXT_SIP_IP}"'"|' "$VARS_XML"
fi

if [ -n "$FS_EXT_RTP_IP" ] && [ -f "$VARS_XML" ]; then
  sed -i 's|data="ext-rtp-ip=[^"]*"|data="ext-rtp-ip='"${FS_EXT_RTP_IP}"'"|' "$VARS_XML"
else
  # default ext-rtp-ip to ext-sip-ip if not set separately
  if [ -n "$FS_EXT_SIP_IP" ] && [ -f "$VARS_XML" ]; then
    sed -i 's|data="ext-rtp-ip=[^"]*"|data="ext-rtp-ip='"${FS_EXT_SIP_IP}"'"|' "$VARS_XML"
  fi
fi

# Inject ESL password
if [ -n "$FS_ESL_PASSWORD" ]; then
  sed -i 's|<param name="password" value="[^"]*"/>|<param name="password" value="'"${FS_ESL_PASSWORD}"'"/>|' \
    /etc/freeswitch/autoload_configs/event_socket.conf.xml
fi

exec /usr/bin/freeswitch "$@"
