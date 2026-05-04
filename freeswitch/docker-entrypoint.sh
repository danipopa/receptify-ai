#!/bin/bash
set -e

VARS_XML=/usr/local/freeswitch/conf/vars.xml
ESL_CONF=/usr/local/freeswitch/conf/autoload_configs/event_socket.conf.xml

# Inject external SIP/RTP IP
if [ -n "$FS_EXT_SIP_IP" ] && [ -f "$VARS_XML" ]; then
  sed -i 's|data="ext-sip-ip=[^"]*"|data="ext-sip-ip='"${FS_EXT_SIP_IP}"'"|' "$VARS_XML"
  sed -i 's|data="ext-rtp-ip=[^"]*"|data="ext-rtp-ip='"${FS_EXT_SIP_IP}"'"|' "$VARS_XML"
fi

if [ -n "$FS_EXT_RTP_IP" ] && [ -f "$VARS_XML" ]; then
  sed -i 's|data="ext-rtp-ip=[^"]*"|data="ext-rtp-ip='"${FS_EXT_RTP_IP}"'"|' "$VARS_XML"
fi

# Inject ESL password
if [ -n "$FS_ESL_PASSWORD" ] && [ -f "$ESL_CONF" ]; then
  sed -i 's|<param name="password" value="[^"]*"/>|<param name="password" value="'"${FS_ESL_PASSWORD}"'"/>|' "$ESL_CONF"
fi

exec /usr/local/freeswitch/bin/freeswitch "$@"
