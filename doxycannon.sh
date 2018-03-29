#!/usr/bin/env bash

read -r -d '' help <<-HELP
Usage: $0 [-u] [-d] [-b]

-u      Brings up a Docker container for each ovpn file in ./VPN
-d      Downs all Docker containers
-b      Builds the required Docker image
HELP

function usage() { echo "$help" 1>&2; exit 1; }

function doxycannon() {
    # delete proxy list from a previous run
    sed -i '10,$d' proxychains.conf

    # starting port
    port=5000

    for f in $(find VPN -name *.ovpn); do
        echo "socks5 127.0.0.1 $port" >> proxychains.conf
        name="$(echo $f | cut -d '/' -f 2)"
        docker run --rm -d --privileged \
            -p 127.0.0.1:$port:1080 \
            -e "VPN=$name" \
            --name="${name}" \
            --dns=8.8.8.8 \
            audibleblink/doxycannon
        port=$((port+1))
    done
}

function build() {
    docker build -t audibleblink/doxycannon .
}

function down() {
    docker ps -q | xargs docker stop
}

[ -z $@ ] && usage

while getopts 'dbu' opt; do
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
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

