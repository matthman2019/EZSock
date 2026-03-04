# Source - https://stackoverflow.com/a/1794373
# Posted by Gordon Wrigley, modified by community. See post 'Timeline' for change history
# Retrieved 2026-03-03, License - CC BY-SA 4.0

import socket

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007
# regarding socket.IP_MULTICAST_TTL
# ---------------------------------
# for all packets sent, after two hops on the network the packet will not 
# be re-sent/broadcast (see https://www.tldp.org/HOWTO/Multicast-HOWTO-6.html)
MULTICAST_TTL = 9

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)

# For Python 3, change next line to 'sock.sendto(b"robot", ...' to avoid the
# "bytes-like object is required" msg (https://stackoverflow.com/a/42612820)
sock.sendto(b"robot", (MCAST_GRP, MCAST_PORT))
print("Sent!")
