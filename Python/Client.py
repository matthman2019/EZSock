import EZSock
from socket import socket

def client_callback(sock : socket, addr : tuple[str, int]):
    print(EZSock.receive_on_socket(sock))

client = EZSock.Client(connect_callback=client_callback)
client.find_server()
client.start()
