FROM signalwire/freeswitch:1.10

# Build and install mod_audio_stream
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential autoconf automake libtool pkg-config \
    && git clone https://github.com/sptmru/freeswitch_mod_audio_stream.git /tmp/mod_audio_stream \
    && cd /tmp/mod_audio_stream && make \
    && cp mod_audio_stream.so /usr/lib/freeswitch/mod/ \
    && rm -rf /tmp/mod_audio_stream \
    && apt-get purge -y git build-essential autoconf automake libtool pkg-config \
    && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Enable mod_audio_stream autoload
RUN sed -i 's|</modules>|  <load module="mod_audio_stream"/>\n</modules>|' \
    /etc/freeswitch/autoload_configs/modules.conf.xml

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 5060/udp 5060/tcp 5080/udp 5080/tcp 8021/tcp 16384-32768/udp

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["-nonat", "-nf"]
