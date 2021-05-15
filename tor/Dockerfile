FROM alpine:3

RUN apk add --no-cache tor && \
	sed "1s/^/SocksPort 0.0.0.0:1080\n/" /etc/tor/torrc.sample > /etc/tor/torrc
VOLUME ["/var/lib/tor"]
USER tor
CMD ["tor"]
