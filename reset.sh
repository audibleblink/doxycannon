#!/bin/bash
# reset.sh
# Swaps out *.ovpn files if you think an IP is burned. Replaces *.ovpn found in the VPN folder with N number of new configs. N is equal to the maximum number of simultaneous connections your VPN provider allows.
# Make sure you have all of your *.ovpn files in a directory named 'configs'

read -p "[+] Enter the number of profiles you want to use: " n
echo "[+] Bringing down the cannon..."
./doxycannon.py --down
echo "[+] Removing current VPN profiles."
rm -r VPN/*.ovpn 2>&1 >/dev/null
for i in $(ls configs/ | sort -R | tail -n $n); do echo "[+] Copying random profile: $i"; cp configs/$i VPN/$i; done
echo "[+] Profiles replaced."
./doxycannon.py --build
echo "[+] Ready, Aim, Fire!"
exit 0
