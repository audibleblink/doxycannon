# doxycannon

Doxycannon takes a pool of OpenVPN files and creates a Docker container for each one that binds a
socks server to a host port. Combined with proxychains, this creates your very own cheap and fast
private botnet.

## Setup
- Create a `VPN` folder in the root of the project 
- Fill it with `*.ovpn` files and ensure that the `auth-user-pass` directive
  in your `./VPN/*.ovpn` files says `auth-user-pass auth.txt`
   - maybe `wget https://www.privateinternetaccess.com/openvpn/openvpn.zip`?
- Create an `auth.txt` file with your ovpn credentials in `VPN`
- Run `./doxycannon.sh -b` to build your image
- Run `./doxycannon.sh -u` to bring your containers up
- Run `./doxycannon.sh -d` to bring your containers down

## Usage

### One-off, random commands
While your containers are up, you can use proxychains to issue commands through random proxies

```sh
proxychains4 -q curl -s ipconfing.io/json
proxychains4 -q hydra -L users.txt -p Winter2018 manager.example.com -t 8 ssh
proxychains4 -q gobuster -w word.list -h http://manager.example.com
```

### Specific SOCKS proxies
If you want to use a specific proxy, give your utility the proper SOCKS port.

IE: To make a request through Japan, use `docker ps` to find the local port the Japanese proxy is
bound to.

Then configure you tool to use that port:

```sh
curl --socks5 localhost:50xx ipconfig.io/json
```

### Interactive
Once you've built your image and started your containers, run the utility with the `-i` flag to get
a bash session where all network traffic is redirected through proxychains4

```sh
./doxycannon.sh -i
```

## Screenshots
![](https://i.imgur.com/jjHtk9L.png)
![](https://i.imgur.com/fLU4Mjx.png)

### Credit
[pry0cc](https://github.com/pry0cc/ProxyDock) for the idea

This was originally a fork of pry0cc/ProxyDock but it's been modified for my needs to an extent
where less than 5% of the origin code remains.

## TODO
I plan on replacing `doxycannon.sh` with a python script that uses the Docker SDK so I can keep
state over which containers have been used for a given command and provide an interactive REPL that
allows commands to be executed through each of the nodes in parallel.
