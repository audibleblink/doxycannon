#!/usr/bin/env bash

read -r -d '' help <<-HELP
Usage: $0 [-u] [-d] [-b] [-i]

-u      Brings up a Docker container for each ovpn file in ./VPN
-d      Downs all Docker containers
-b      Builds the required Docker image
-i      Starts an interactive shell with proxied network connections. Requires running containers
HELP

function usage() { echo "$help" 1>&2; exit 1; }

function doxycannon() {
    # delete proxy list from a previous run
    sed -i '10,$d' proxychains.conf

    # starting port
    port=5000

    for file in $(find VPN -maxdepth 1 -name *.ovpn); do
        echo "socks5 127.0.0.1 ${port}" >> proxychains.conf
        name="$(basename -s .ovpn ${file})"
        docker run --rm -d --privileged \
            -p ${port}:1080 \
            -e "VPN=${name}" \
            --name="${name}" \
            --dns=8.8.8.8 \
            audibleblink/doxycannon
        port=$((port+1))
    done
}

function interactive() {
    proxychains4 bash
}

function build() {
    docker build -t audibleblink/doxycannon .
}

function down() {
    docker ps -q | xargs docker stop
}

[ -z $@ ] && usage

while getopts 'dbui' opt; do
    case "${opt}" in
        b)
            build
            ;;
        d)
            down
            ;;
        u)
            doxycannon
            ;;
        i)
            interactive
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

