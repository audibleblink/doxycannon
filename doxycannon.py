import argparse
import docker
import glob
import re
import os
from Queue import Queue
from threading import Thread

VERSION = '0.1.0'
IMAGE = 'audibleblink/doxycannon'
THREADS = 20
START_PORT = 5000
SOCKS_PORT = 1080

PROXYCHAINS_CONF = './proxychains.conf'
PROXYCHAINS_TEMPLATE = """
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
        bind *:1337
        mode tcp
        balance roundrobin
        default_backend doxycannon

backend doxycannon
"""

doxy = docker.from_env()

def build(image_name):
    try:
        image = doxy.images.build(path='.', tag=image_name)
        print "[*] Image {} built. Use --up to bring up your containers".format(image_name)
    except Exception as err:
        print err
        raise

def vpn_file_queue(dir):
    files = glob.glob(dir + '/*.ovpn')
    jobs = Queue(maxsize=0)
    for file in files:
        jobs.put(file)
    return jobs

def write_config(filename, data, type):
    with open(filename, 'w') as file:
        if type == 'haproxy':
            file.write(HAPROXY_TEMPLATE)
        elif type == 'proxychains':
            file.write(PROXYCHAINS_TEMPLATE)
        for line in data:
            file.write(line + "\n")

# Writes the HAProxy config file in `./haproxy` to reflect the number
# of Docker containers about to be started
def write_haproxy_conf(port_range):
    print "[+] Writing HAProxy configuration"
    conf_line = "\tserver doxy{} 127.0.0.1:{} check"
    data = list(map(lambda x: conf_line.format(x,x), port_range))
    write_config(HAPROXY_CONF, data, 'haproxy')

# Writes the Proxychains config file to reflect the number
# of Docker containers about to be started
def write_proxychains_conf(port_range):
    print "[+] Writing Proxychains configuration"
    conf_line = "socks5 127.0.0.1 {}"
    data = list(map(lambda x: conf_line.format(x), port_range))
    write_config(PROXYCHAINS_CONF, data, 'proxychains')

# Returns a Queue of containers whose source image match the given image name
def containers_from_image(image_name):
    jobs = Queue(maxsize=0)
    filter_func = lambda x: image_name in x.attrs['Config']['Image']
    containers = list(filter(filter_func, doxy.containers.list()))
    [ jobs.put(container) for container in containers ]
    return jobs

# Handle to job killer. Called by the Thread worker function.
def multikill(jobs):
    while True:
        container = jobs.get()
        print 'Stopping: {}'.format(container.name)
        container.kill(9)
        jobs.task_done()

# Find all containers from an image name and start workers for them.
# The workers are tasked with running the job killer function
def stop_containers_from_image(image_name):
    container_queue = containers_from_image(image_name)
    for i in range(THREADS):
        worker = Thread(target=multikill, args=(container_queue,))
        worker.setDaemon(True)
        worker.start()
    container_queue.join()
    print '[+] All containers stopped!'

def multistart(jobs, ports):
    while True:
        port = ports.get()
        ovpn_basename = os.path.basename(jobs.get())
        ovpn_stub = re.sub("\.ovpn", "", ovpn_basename)
        print 'Starting: {}'.format(ovpn_stub)
        doxy.containers.run(
            IMAGE, 
            auto_remove=True,
            privileged=True,
            ports={'1080/tcp': ('127.0.0.1', port)},
            dns=['1.1.1.1'],
            environment=["VPN={}".format(ovpn_basename)],
            name=ovpn_stub,
            detach=True)
        port = port + 1
        jobs.task_done()

def start_containers(image_name, ovpn_queue, amount):
    port_queue = Queue(maxsize=0)
    for p in range(START_PORT, START_PORT + amount):
        port_queue.put(p)

    for i in range(THREADS):
        worker = Thread(target=multistart, args=(ovpn_queue,port_queue,))
        worker.setDaemon(True)
        worker.start()
    ovpn_queue.join()
    print '[+] All containers started!'

def up(image):
    ovpn_file_queue = vpn_file_queue('./VPN')
    ovpn_list = list(ovpn_file_queue.queue)
    amount = len(ovpn_list)
    write_haproxy_conf(amount)
    write_proxychains_conf(amount)
    start_containers(image, ovpn_file_queue, amount)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--build',
        action='store_true',
        default=False,
        dest='build',
        help='Builds the base docker image')
    parser.add_argument(
        '--up',
        action='store_true',
        default=False,
        dest='up',
        help='Brings up containers. 1 for each VPN file in ./VPN')
    parser.add_argument(
        '--down',
        action='store_true',
        default=False,
        dest='down',
        help='Bring down all the containers')
    parser.add_argument('--version', action='version', version="%(prog)s {}".format(VERSION))
    args = parser.parse_args()

    if args.build:
        build(IMAGE)
    elif args.up:
        up(IMAGE)
    elif args.down:
        down(IMAGE)
    elif args.interactive:
        interactive(IMAGE)

if __name__ == "__main__":
    main()
