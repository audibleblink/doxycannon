#!/bin/bash
# Name: reset.sh
# Desc: Replaces the OpenVPN configuration files found in the VPN folder with N number of new configs.
# N is equal to the maximum number of simultaneous connections your VPN provider allows.
# Make sure you have all of your *.ovpn files in a directory named 'configs'
# Make sure you run this from the project root folder
# Make sure all your config files have had the following parameters replaced:
#	sed -i 's/pass/pass auth.txt/' *.ovpn
#	sed -i 's/up \/etc\/openvpn\/update-resolv-conf/up \/etc\/openvpn\/up.sh/g' *.ovpn
#	sed -i 's/down \/etc\/openvpn\/update-resolv-conf/down \/etc\/openvpn\/down.sh/g' *.ovpn

read -r -p "[+] Enter the number of profiles you want to use: " n
read -r -p "[+] Enter the first two letters of a country: " country # ProtonVPN configuration specific
echo "[+] Bringing down the cannon..."
./doxycannon.py --down
echo "[+] Removing current VPN profiles."
rm -r VPN/*.ovpn 2>&1 >/dev/null
for i in $(ls configs/$country* | sort -R | tail -n $n | sed 's/configs\///g'); do echo "[+] Copying random profile: $i"; cp configs/$i VPN/$i; done
echo "[+] Profiles replaced."
./doxycannon.py --build
echo "[+] Use \`./doxycannon.py --up\` or \`./doxycannon.py --single\` when prepared."
echo "[+] Ready, Aim, Fire!"
exit 0
