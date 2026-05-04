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

WORKDIR /usr/src

RUN git clone https://github.com/signalwire/freeswitch.git freeswitch
RUN git clone https://github.com/sptmru/freeswitch_mod_audio_stream.git freeswitch_mod_audio_stream

WORKDIR /usr/src/freeswitch

RUN git checkout ${FS_VERSION}

# Copy external module into FreeSWITCH source tree
RUN mkdir -p /usr/src/freeswitch/src/mod/applications/mod_audio_stream && \
    cp -a /usr/src/freeswitch_mod_audio_stream/. \
          /usr/src/freeswitch/src/mod/applications/mod_audio_stream/

# Enable mod_audio_stream
RUN echo "applications/mod_audio_stream" >> modules.conf

RUN ./bootstrap.sh -j

RUN ./configure \
    --prefix=/usr/local/freeswitch \
    --with-openssl \
    --enable-core-pgsql-support

RUN make -j$(nproc)

RUN make install

RUN make sounds-install moh-install

# Load mod_audio_stream automatically
RUN sed -i 's|</modules>|  <load module="mod_audio_stream"/>\n</modules>|' \
    /usr/local/freeswitch/conf/autoload_configs/modules.conf.xml

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 5060/udp 5060/tcp 5080/udp 5080/tcp 8021/tcp 16384-32768/udp

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["-nonat", "-nf"]
