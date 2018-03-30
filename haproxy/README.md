# doxyproxy

This Docker image creates an haproxy instance bound to the host network that will roundrobin
through your doxycannon proxies. This allows you to use a single socks5 proxy server to point
things like browsers and GUI tools... like BURPSuite

## Running the container

```sh
docker build -t haproxy .
docker run -p 1337:1337 --rm --network host --name doxyproxy haproxy
```

Then just point {burp,firefox,etc} at socks5://127.0.0.1:1337
