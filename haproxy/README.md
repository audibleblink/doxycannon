# doxyproxy

This Docker image creates an haproxy instance bound to the host network that will roundrobin
through your doxycannon proxies. This allows you to use a single socks5 proxy server to which you
point things like browsers and BURPSuite

## Running the container

You will need to build every time the config file is modified.
To build the config file, first run the doxyproxy.py file with the `--up` flag

```sh
docker build -t haproxy .
docker run --rm --network host --name doxyproxy haproxy
```

Then just point {burp,firefox,etc} at socks5://127.0.0.1:1337
