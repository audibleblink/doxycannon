FROM alpine:latest

# Install packages
RUN apk --no-cache add openvpn dante-server supervisor && \
	rm -rf /var/cache/

# Add image configuration and scripts
ADD VPN /VPN
ADD etc/ /etc/

EXPOSE 1080
CMD ["supervisord","-n"]
