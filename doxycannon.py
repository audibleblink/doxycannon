#!/usr/bin/env python3

import argparse
import os
import re
import signal
import sys

from pathlib import Path
from threading import Thread
from queue import Queue

import docker

VERSION = '0.5.0'
IMAGE = 'audibleblink/doxycannon'
TOR = 'audibleblink/tor'
DOXY = 'audibleblink/doxyproxy'

THREADS = 10
START_PORT = 9000
HAPORT = 1337

PROXYCHAINS_CONF = './proxychains.conf'
PROXYCHAINS_TEMPLATE = """
# This file is automatically generated by doxycannon. If you need changes,
# make them to the template string in doxycannon.py
random_chain
quiet_mode
proxy_dns
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000

[ProxyList]
"""

HAPROXY_CONF = './haproxy/haproxy.cfg'
HAPROXY_TEMPLATE = """
# This file is automatically generated by doxycannon. If you need changes,
# make them to the template string in doxycannon.py
global
        daemon
        user root
        group root

defaults
        mode tcp
        maxconn 3000
        timeout connect 5000ms
        timeout client 50000ms
        timeout server 50000ms

listen funnel_proxy
        bind *:{}
        mode tcp
        balance roundrobin
        default_backend doxycannon

backend doxycannon
""".format(HAPORT)


def build(image, path='.'):
    """Builds the image with the given name"""
    try:
        doxy.images.build(path=path, tag=image, forcerm=True)
        message = '[+] Image {} built.'
        print(message.format(image))
    except Exception as err:
        print(err)
        raise


def vpn_file_queue(folder):
    """Returns a Queue of files from the given directory"""
    files = Path(folder).rglob('*.ovpn')
    # files = glob.glob(folder + '/**/*.ovpn')
    jobs = Queue(maxsize=0)
    for f in files:
        jobs.put(f)
    return jobs


def write_config(filename, data, conf_type):
    """ Write data to a given filename

    The `type` argument determines what template gets written
    at the beginning of the config file. Types are either
    'haproxy' or 'proxychains'
    """
    with open(filename, 'w') as f:
        if conf_type == 'haproxy':
            f.write(HAPROXY_TEMPLATE)
        elif conf_type == 'proxychains':
            f.write(PROXYCHAINS_TEMPLATE)
        for line in data:
            f.write(line + "\n")


def write_haproxy_conf(names, port_range):
    """Generates HAProxy config based on # of ovpn files"""
    print("[+] Writing HAProxy configuration")

    conf_line = "\tserver doxy{0} {1}:1080 check"

    data = list(map(lambda x: conf_line.format(x[0], x[1]), zip(port_range, names)))

    write_config(HAPROXY_CONF, data, 'haproxy')


def write_proxychains_conf(port_range):
    """Generates Proxychains4 config based on # of ovpn files"""
    print("[+] Writing Proxychains4 configuration")
    conf_line = "socks5 127.0.0.1 {}"
    data = list(map(lambda x: conf_line.format(x), port_range))
    write_config(PROXYCHAINS_CONF, data, 'proxychains')


def containers_from_image(image, all=False):
    """Returns a Queue of containers whose source image match image"""
    jobs = Queue(maxsize=0)
    containers = list(
        filter(
            lambda x: image in x.attrs['Config']['Image'],
            doxy.containers.list(all=all)
        )
    )
    for container in containers:
        jobs.put(container)
    return jobs


def multikill(jobs):
    """Handler to job killer. Called by the Thread worker function."""
    while True:
        container = jobs.get()
        print('Stopping: {}'.format(container.name))
        container.kill(9)
        jobs.task_done()


def delete_container(jobs):
    """Handler to clean task. Called by the Thread worker function."""
    while True:
        container = jobs.get()
        print('Deleting: {}'.format(container.name))
        container.remove(force=True)
        jobs.task_done()


def clean(image):
    """Find all containers with <image> in the imagename and
    delete them.
    """
    container_queue = containers_from_image(image, all=True)
    for _ in range(THREADS):
        worker = Thread(target=delete_container, args=(container_queue,))
        worker.setDaemon(True)
        worker.start()
    container_queue.join()
    print("[+] Deleted all containers based on image {}".format(image))


def down(image):
    """Find all containers from an image name and start workers for them.
    The workers are tasked with running the job killer function
    """
    container_queue = containers_from_image(image)
    for _ in range(THREADS):
        worker = Thread(target=multikill, args=(container_queue,))
        worker.setDaemon(True)
        worker.start()
    container_queue.join()

    try:
        doxy.networks.get("doxy_network").remove()
    except:
        print("[?] Network won't be removed as containers are still running.")

    print("[+] All containers based on {} have been issued a kill command".format(image))


def multistart(image, jobs, ports):
    """Handler for starting containers. Called by Thread worker function."""
    while True:
        port = ports.get()
        config = jobs.get()
        # if config is str, then multistart was called from tor command. Else, config is PosixPath
        if isinstance(config, str):
            container_name = config
            parent = 'tor'
        else:
            container_name = re.sub(".ovpn", "", config.name)
            parent = config.parent

        print('Starting: {} on port {}, path is {}'.format(container_name, port, parent))

        try:
            doxy.containers.run(
                image,
                auto_remove=True,
                privileged=True,
                ports={'1080/tcp': ('127.0.0.1', port)},
                network='doxy_network',
                environment=["VPN={}".format(container_name), "VPNPATH=/{}".format(parent)],
                name=container_name,
                detach=True)
        except docker.errors.APIError as err:
            print(err.explanation)
            print("[*] Run doxycannon --clean to deletes conflicting containers")

        # port = port + 1
        ports.task_done()
        jobs.task_done()


def start_containers(image, ovpn_queue, port_range):
    """Starts workers that call the container creation function"""
    port_queue = Queue(maxsize=0)
    for p in port_range:
        port_queue.put(p)

    for _ in range(THREADS):
        worker = Thread(
            target=multistart,
            args=(image, ovpn_queue, port_queue,))
        worker.setDaemon(True)
        worker.start()
    ovpn_queue.join()
    print('[+] All containers have been issued a start command')


def up(image, conf):
    """Kick off the `up` process that starts all the containers

    Writes the configuration files and starts starts container based
    on the number of *.ovpn files in the VPN folder
    """

    try:
        doxy.networks.get("doxy_network")
        print("[?] Network already exists")
    except docker.errors.NotFound:
        doxy.networks.create("doxy_network", driver="bridge", attachable=True)

    if not doxy.images.list(name=image):
        build(image)

    ovpn_file_queue = vpn_file_queue(conf)
    print("[+] List of VPN files:")
    for p in list(ovpn_file_queue.queue):
        print("\t[?]", str(p))

    ovpn_file_count = len(list(ovpn_file_queue.queue))

    names = [re.sub(".ovpn", "", name.name) for name in ovpn_file_queue.queue]

    port_range = range(START_PORT, START_PORT + ovpn_file_count)
    write_haproxy_conf(names, port_range)
    write_proxychains_conf(port_range)
    start_containers(image, ovpn_file_queue, port_range)


def tor(count):
    """Start <count> tor nodes to proxy through

    Will take the given number of tor nodes and start a proxy
    rotator that cycles through the tor nodes
    """
    if not doxy.images.list(name=TOR):
        build(TOR, path='./tor/')

    try:
        doxy.networks.get("doxy_network")
        print("[?] Network already exists")
    except docker.errors.NotFound:
        doxy.networks.create("doxy_network", driver="bridge", attachable=True)

    port_range = range(START_PORT, START_PORT + count)
    name_queue = Queue(maxsize=0)
    names = []
    for port in port_range:
        name_queue.put("tor_{}".format(port))
        names.append(f"tor_{port}")

    write_haproxy_conf(names, port_range)
    start_containers(TOR, name_queue, port_range)


def rotate():
    """Creates a proxy rotator, HAProxy, based on the port range provided"""
    try:
        build(DOXY, path='./haproxy')
        print('[*] Staring single-port mode...')
        print(f"[*] Proxy rotator listening on port {HAPORT}. Ctrl-c to quit")
        signal.signal(signal.SIGINT, signal_handler)
        cname = DOXY.split("/")[1]

        doxy.containers.run(DOXY, name=cname, auto_remove=True, network='doxy_network', ports={f"{HAPORT}/tcp": ('127.0.0.1', HAPORT)})

    except Exception as err:
        print(err)
        raise


def single(image, conf=None, nodes=None):
    """Starts an HAProxy rotator.

    Builds and starts the HAProxy container in the haproxy folder
    This will create a local socks5 proxy on port $HAPORT that will
    allow one to configure applications with SOCKS proxy options.
    Ex: Firefox, BurpSuite, etc.
    """

    if not list(containers_from_image(image).queue):
        if nodes:
            tor(args.nodes)
        elif conf:
            up(image, conf)

    rotate()


def interactive(image, conf):
    """Starts the interactive process. Requires Proxychains4

    Creates a shell session where network connections are routed through
    proxychains. Started GUI application from here rarely works
    """
    try:
        if not list(containers_from_image(image).queue):
            up(image, conf)
        else:
            ovpn_file_count = len(list(vpn_file_queue(args.dir).queue))
            port_range = range(START_PORT, START_PORT + ovpn_file_count)
            write_proxychains_conf(port_range)

        os.system("proxychains4 zsh")
    except Exception as err:
        print(err)
        raise


def signal_handler(*args):
    """Traps ctrl+c for cleanup, then exits"""
    sys.stdout = open(os.devnull, 'w')
    if list(containers_from_image(DOXY).queue):
        down(DOXY)

    sys.stdout = sys.__stdout__
    print('\n[*] {} was issued a stop command'.format(DOXY))
    print('[*] Your proxies are still running.')
    sys.exit(0)


def get_parsed():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    tor_cmd = subparsers.add_parser('tor', help="tor --help")
    tor_cmd.add_argument(
        '--nodes',
        type=int,
        default=3,
        dest="nodes",
        # required=True,
        help="Number of tor nodes to rotate through. Default: 3")
    tor_cmd.add_argument(
        '--up',
        action='store_true',
        default=False,
        dest='up',
        help='Brings up tor containers. 1 for each [--nodes]')
    tor_cmd.add_argument(
        '--down',
        action='store_true',
        default=False,
        dest='down',
        help='Bring down all tor containers')
    tor_cmd.add_argument(
        '--single',
        action='store_true',
        default=False,
        dest='single',
        help='Start an HAProxy rotator on a single port. Useful for Burpsuite')
    tor_cmd.add_argument(
        '--clean',
        action='store_true',
        default=False,
        dest='clean',
        help='Delete all dangling tor containers. Useful for duplicate container errors')

    vpn_cmd = subparsers.add_parser('vpn', help="vpn --help")
    vpn_group = vpn_cmd.add_mutually_exclusive_group()
    vpn_group.add_argument(
        '--up',
        action='store_true',
        default=False,
        dest='up',
        help='Brings up containers. 1 for each VPN file in [dir]')

    vpn_cmd.add_argument(
        '--down',
        action='store_true',
        default=False,
        dest='down',
        help='Bring down all the containers')

    vpn_cmd.add_argument(
        '--single',
        action='store_true',
        default=False,
        dest='single',
        help='Start an HAProxy rotator on a single port. Useful for Burpsuite')

    vpn_cmd.add_argument(
        '--clean',
        action='store_true',
        default=False,
        dest='clean',
        help='Delete all dangling VPN containers. Useful for duplicate container errors')

    vpn_cmd.add_argument(
        '--dir',
        default="VPN",
        dest='dir',
        help='Specify a directory to use for VPN config')

    vpn_cmd.add_argument(
        '--interactive',
        action='store_true',
        default=False,
        dest='interactive',
        help="Starts an interactive bash session where network connections" +
        " are routed through proxychains. Requires proxychainvs v4+")

    vpn_cmd.add_argument(
        '--build',
        action='store_true',
        default=False,
        dest='build',
        help='Build doxyproxy image.')

    parser.add_argument(
        '--nuke',
        action='store_true',
        default=False,
        dest='nuke',
        help='Delete all dangling vpn, tor, doxyproxy containers.')

    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s {}".format(VERSION))

    return parser.parse_args()


def handle_tor(args):
    if args.clean:
        clean(TOR)
    elif args.up:
        tor(args.nodes)
    elif args.down:
        down(TOR)
    elif args.single:
        single(TOR, nodes=args.nodes)


def handle_vpn(args):
    if args.clean:
        clean(IMAGE)
    elif args.build:
        build(IMAGE)
    elif args.up:
        up(IMAGE, args.dir)
    elif args.down:
        down(IMAGE)
    elif args.single:
        single(IMAGE, conf=args.dir)
    elif args.interactive:
        interactive(IMAGE, args.dir)


def main(args):
    if args.command == "tor":
        handle_tor(args)
    elif args.command == "vpn":
        handle_vpn(args)
    elif args.nuke:
        for i in [IMAGE, TOR, DOXY]:
            clean(i)
            try:
                network = doxy.networks.get("doxy_network")
                network.remove()
                doxy.images.remove(i)
                print("[+] Image {} deleted".format(i))
            except docker.errors.APIError as err:
                print("[!] {}".format(err.explanation))


if __name__ == "__main__":
    try:
        doxy = docker.from_env()
    except Exception:
        print("Unable to contact local Docker daemon. Is it running?")
        sys.exit(1)
    args = get_parsed()
    main(args)

