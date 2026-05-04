FROM signalwire/freeswitch:1.10

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 5060/udp 5060/tcp 5080/udp 5080/tcp 8021/tcp 16384-32768/udp

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["-nonat", "-nf"]
