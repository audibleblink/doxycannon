FROM alpine:3.7

# Install packages
RUN echo 'http://dl-4.alpinelinux.org/alpine/edge/testing' >> /etc/apk/repositories && \
	apk --no-cache add openvpn dante-server supervisor && \
	rm -rf /var/cache/

# Add image configuration and scripts
ADD VPN /VPN
ADD etc/ /etc/

EXPOSE 1080
CMD ["supervisord","-n"]
