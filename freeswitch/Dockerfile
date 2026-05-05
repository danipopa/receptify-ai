FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV FS_VERSION=v1.10.12

RUN apt-get update && apt-get install -y \
    git curl wget ca-certificates \
    build-essential autoconf automake libtool libtool-bin \
    pkg-config cmake m4 make gcc g++ \
    yasm nasm \
    uuid-dev zlib1g-dev \
    libssl-dev libcurl4-openssl-dev \
    libsqlite3-dev \
    libpcre3-dev libpcre2-dev \
    libedit-dev libldns-dev libncurses-dev \
    libopus-dev libspeex-dev libspeexdsp-dev \
    libsndfile1-dev libflac-dev libogg-dev \
    libavcodec-dev libavformat-dev libavutil-dev \
    libjpeg-dev libpng-dev libtiff-dev \
    libpq-dev libmariadb-dev libpcap-dev \
    liblua5.2-dev \
    python3 python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Build SpanDSP
RUN git clone https://github.com/freeswitch/spandsp.git /usr/src/spandsp \
    && cd /usr/src/spandsp \
    && ./bootstrap.sh \
    && ./configure \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && rm -rf /usr/src/spandsp

# Build Sofia-SIP
RUN git clone https://github.com/freeswitch/sofia-sip.git /usr/src/sofia-sip \
    && cd /usr/src/sofia-sip \
    && ./bootstrap.sh \
    && ./configure \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && rm -rf /usr/src/sofia-sip

WORKDIR /usr/src

RUN git clone https://github.com/signalwire/freeswitch.git freeswitch
RUN git clone --recurse-submodules https://github.com/sptmru/freeswitch_mod_audio_stream.git freeswitch_mod_audio_stream

WORKDIR /usr/src/freeswitch

RUN git checkout ${FS_VERSION}

RUN ./bootstrap.sh -j

# Disable modules not needed for AI receptionist / problematic deps
RUN sed -i \
    -e 's|^[#[:space:]]*applications/mod_signalwire|#applications/mod_signalwire|' \
    -e 's|^[#[:space:]]*applications/mod_av|#applications/mod_av|' \
    -e 's|^[#[:space:]]*applications/mod_spandsp|#applications/mod_spandsp|' \
    -e 's|^[#[:space:]]*applications/mod_fax|#applications/mod_fax|' \
    -e 's|^[#[:space:]]*endpoints/mod_verto|#endpoints/mod_verto|' \
    modules.conf

RUN ./configure \
    --prefix=/usr/local/freeswitch \
    --with-openssl \
    --enable-core-pgsql-support

RUN make -j$(nproc)
RUN make install
RUN make samples
RUN make sounds-install moh-install

ENV PKG_CONFIG_PATH=/usr/local/freeswitch/lib/pkgconfig:/usr/local/lib/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig
ENV LD_LIBRARY_PATH=/usr/local/freeswitch/lib:/usr/local/lib

# Build mod_audio_stream
RUN mkdir -p /usr/src/freeswitch_mod_audio_stream/build \
    && cd /usr/src/freeswitch_mod_audio_stream/build \
    && cmake -DCMAKE_BUILD_TYPE=Release .. \
    && make -j$(nproc) \
    && cp mod_audio_stream.so /usr/local/freeswitch/lib/freeswitch/mod/

# Load mod_audio_stream automatically
RUN MODULES_CONF="$(find /usr/local/freeswitch -name modules.conf.xml | head -n 1)" \
    && echo "Using modules config: ${MODULES_CONF}" \
    && sed -i 's|</modules>|  <load module="mod_audio_stream"/>\n</modules>|' "$MODULES_CONF"

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 5060/udp 5060/tcp 5080/udp 5080/tcp 8021/tcp 16384-32768/udp

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["-nonat", "-nf"]