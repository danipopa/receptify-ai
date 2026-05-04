FROM signalwire/freeswitch:1.10

# Copy custom config if present
COPY conf/ /etc/freeswitch/

EXPOSE 5060/udp 5060/tcp 5080/udp 5080/tcp 8021/tcp 16384-32768/udp

CMD ["/usr/bin/freeswitch", "-nonat", "-nf"]
