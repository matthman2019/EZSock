import EZSock
from socket import socket

def serverCallback(sock : socket, addr : tuple[str, int]):
    EZSock.send_on_socket(sock, {"title":"Hello There!"})


s = EZSock.Server(accept_callback=serverCallback)
s.start()


