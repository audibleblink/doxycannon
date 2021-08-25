# doxycannon

[![CodeFactor](https://www.codefactor.io/repository/github/audibleblink/doxycannon/badge)](https://www.codefactor.io/repository/github/audibleblink/doxycannon)

Doxycannon uses docker to create multiple socks proxies where the upstream
internet connections are either VPN connections or Tor nodes

In VPN mode, it takes a pool of OpenVPN files and creates a Docker container for
each one. After a successful VPN connection, each container spawns a SOCKS5
proxy server and binds it to a port on the Docker host. 

In Tor mode, containers initiate a connection to the Tor network. 

Both VPN and Tor nodes can be rotated through, giving you a new egress IP with each request.

Combined with tools like Burp suite or proxychains, this creates your very own (small) private 
botnet on the cheap.

[Password Spraying Blog Post Using DoxyCannon](https://sec.alexflor.es/post/password_spraying_with_doxycannon/)

## Prerequisites

If using VPN mode, you'll need a VPN subscription to a provider that distributes `*.ovpn` files

- Install the required pip modules:
  ```sh
  pip install -r requirements.txt
  ```

- Ensure docker is installed and enabled. Refer to the
  [Wiki](../../wiki/installing-docker) for installation instructions on
  Kali/Debian

- `proxychains4` is required for interactive mode

## Setup
<<<<<<< HEAD
- Create a `NAME.txt` file with your ovpn credentials in `VPN`. The format is:
=======
<<<<<<< HEAD
- Create a `NAME.txt` file with your ovpn credentials in `VPN`. The format is:
=======
- Create an `NAME.txt` file with your ovpn credentials in `VPN`. The format is:
>>>>>>> bbcd56e (fix readme)
>>>>>>> c26ac4b (update)
  ```txt
  username
  password
  ```
- Fill the VPN folder with `*.ovpn` files and ensure that the `auth-user-pass`
  directive in your `./VPN/*.ovpn` files says `auth-user-pass NAME.txt`
   - Check out [this wiki section](../../wiki#getting-started-with-vpn-providers)
     for installation instructions for individual VPN providers
- Within the VPN folder, you may divide/organize your VPN file into subdirectories
     and use the `--dir` flag with the `--up` or `--single` commands to only use 
     those configs

     ```sh
     mkdir -p VPN/US
     mv US.opvn auth-us.txt VPN/US
     doxycannon vpn --dir VPN/US --up

     mkdir -p VPN/FR
     mv FR.opvn auth-fr.txt VPN/FR
     doxycannon vpn --dir VPN/FR --up
     ```

- If `--dir` is equal to `VPN`, a container will be launched for each `ovpn` file inside the folder. Use `--single` to have HAproxy load-balance between all VPNs.
    ```sh
<<<<<<< HEAD
=======
     doxycannon vpn --dir VPN --up
>>>>>>> c26ac4b (update)
     doxycannon vpn --dir VPN --single # Launch HAproxy to load balance
     ```

- `--single` does not stop proxy containers when it quits, it only stops HAproxy. Use `--down` to bring them down.

- Alternatively, use the `tor` subcommand to just spin up tor nodes

    ```sh
    doxycannon tor --nodes 7 --single
    ```

## Usage
_note_: Before 14 May 21, versions of [rofl0r/proxychains-ng](https://github.com/rofl0r/proxychains-ng) use a 
second-based seed for the PRNG that determines random proxy selection. Be sure to use a version based on or 
after this [commit](https://github.com/rofl0r/proxychains-ng/commit/092d7042e092a033ac0c33a238927050c2cc7de0)


### One-off, random commands
While your containers are up, you can use proxychains-ng to issue commands through
random proxies

```sh
proxychains4 -q curl -s ipconfig.io/json
proxychains4 -q hydra -L users.txt -p Winter2020 manager.example.com -t 8 ssh
```

### GUI Tools

Use the `--single` flag to create a proxy rotator.

```sh
❯❯ ./doxycannon.py [vpn|tor] --single
[+] Writing HAProxy configuration
[*] Image doxyproxy built.
[*] Staring single-port mode...
[*] Proxy rotator listening on port 1337. Ctrl-c to quit
^C
[*] doxyproxy was issued a stop command
[*] Your proxies are still running.
```

To see what's happening, checkout out the [haproxy](haproxy) folder.  Essentially, the tool builds
a layer 4 load-balancer between all the VPNs. This allows rotatation of proxies through a single
port. One can then point browsers or BURPSuite at it and have every request use a
different VPN.

### Specific SOCKS proxies

Example: To make a request through Japan, use `docker ps` and find the local
port to which the Japanese VPN is bound.

Configure your tool to use that port:

```sh
curl --socks5 localhost:50xx ipconfig.io/json
```

### Interactive
Once you've started your containers, run the utility with
the `--interactive` flag to get a bash session where all network traffic is
redirected through proxychains4

```sh
./doxycannon.py --interactive
```


### Credit
[pry0cc](https://github.com/pry0cc/ProxyDock) for the idea

This was originally a fork of pry0cc's ProxyDock. It's been modified to an
extent where less than 1% of the original code remains.
