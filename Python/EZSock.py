import socket
import time
import logging
from logging import debug, info, warning, error
import threading
from typing import Callable
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)


BROADCASTPORT = 56767
PORT = 26767
# Mega thanks to gemini for the following 3 functions!

def get_local_ip():
    """
    Attempts to find the local IP address by connecting to a public IP.
    """
    s = None
    try:
        # Create a temporary socket to an external address (e.g., Google DNS)
        # This only establishes the connection attempt locally and determines the
        # correct local interface IP to use for routing to that destination.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        return ip_address
    except socket.error:
        # Fallback for systems without a network connection (e.g. returns 127.0.0.1)
        return socket.gethostbyname(socket.gethostname())
    finally:
        if s:
            s.close()

def server_broadcast_daemon(ip : str = "192.168.1.255", port : int=BROADCASTPORT): 
    """
    Code taken from Gemini.
    This function is a daemon for a server. It UDP broadcasts its ip and port.
    """
    global BROADCASTPORT
    MESSAGE = f"EZSOCK SERVER {ip} {port}".encode()

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Enable broadcasting mode
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        sock.sendto(MESSAGE, ('<broadcast>', BROADCASTPORT))
        debug(f"Message sent: {MESSAGE!r}")
        time.sleep(1)

def get_address_from_broadcast(timeout = 10):
    """
    Code taken from gemini.
    Listens for UDP broadcasts to get address.
    """
    UDP_IP = "0.0.0.0"  # Listen on all available interfaces
    global BROADCASTPORT

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    # Bind to the port
    sock.bind((UDP_IP, BROADCASTPORT))

    debug(f"Listening for UDP packets on port {BROADCASTPORT}")
    try:
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        debug(f"Received message: {data!r} from {addr}")
    except TimeoutError:
        error(f"Timed out! Received no UDP broadcasts on port {BROADCASTPORT}.")
        return
     
    ip = addr[0]
    port = int(data.split()[3])
    return (ip, port)

def get_address_from_file():
    """
    Looks for .connection files in the parent folder.
    It uses the first file it finds, searching the parent folder first then doing a depth first search.
    """
    parentFolder = Path(__file__).parent
    connectionFile = None
    def parseFolder(folder : Path):
        for item in folder.iterdir():
            assert isinstance(item, Path)
            if item.is_dir():
                continue
            if item.suffix.lstrip(".") == "connect":
                return item
        for item in folder.iterdir():
            if not item.is_dir():
                continue
            returnVal = parseFolder(item)
            if returnVal:
                return returnVal
    connectionFile = parseFolder(parentFolder)

    if not connectionFile:
        warning("Could not find .connect file!")
        return

    connectionFile = parseFolder(parentFolder)
    address = ""
    port = 0
    with open(connectionFile, 'r') as file:
        for line in file:
            line = line.rstrip('\n')
            lineList = list(map(lambda x: x.strip(), line.split("|")))
            if lineList[0] == "addr":
                address = lineList[1]
            if lineList[0] == "port":
                port = int(lineList[1])
    return (address, port)


# functions to help send and receive json data easily
def send_on_socket(sock : socket.socket, data : dict):
    """Sends a dictionary over a socket. It encodes the dictionary as utf-8 json."""
    jsonData = json.dumps(data).encode()
    sock.sendall(jsonData)
def receive_on_socket(sock : socket.socket) -> dict:
    received = ""
    receivedDict = None
    done = False
    i = 0
    while not done:
        received = sock.recv(2048)
        try:
            receivedDict = json.loads(received)
            done = True
        except Exception:
            pass
    return receivedDict


class Server:
    """
    The server class. 
    It holds a server socket and integrates with threading to make lives easier.
    """

    def __init__(self, addr : tuple[str, int] = ("0.0.0.0", PORT), timeout : int = 5, reuse_addr : bool = True, accept_callback : Callable[[socket.socket, tuple[str, int]], None] = None):
        
        if not accept_callback:
            accept_callback = lambda client, _: (warning("You need to add functionality for the server's accept_callback!"), client.close())

        self.addr : tuple[str, int] = addr
        self.reuse_addr : bool = reuse_addr
        self.socket : socket.socket = None
        self.timeout : int = timeout
        self.thread_list : list[threading.Thread] = []
        self.self_thread : threading.Thread = None
        self.broadcast_thread : threading.Thread = None
        self.accept_callback : Callable[[socket.socket, tuple[str, int]], None] = accept_callback


    def run(self):
        # start udp broadcast daemon
        self.broadcast_thread = threading.Thread(target=server_broadcast_daemon)
        self.broadcast_thread.start()

        # set up server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        if self.reuse_addr:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.socket.bind(self.addr)
        self.socket.listen()
        info(f"Server is up and listening! Address: {self.addr}")
        
        while True:
            try:
                client, clientAddr = self.socket.accept()
                debug(f"Received connection! Address: {clientAddr}")
                t = threading.Thread(target=self.accept_callback, args=(client, clientAddr))
                t.start()
                self.thread_list.append(t)
            except TimeoutError:
                debug(f"Timed out! {time.time()}")

    def start(self, daemon=False):
        """Like self.run(), but runs asynchronously using threading."""
        self.self_thread = threading.Thread(target=self.run, daemon=daemon)
        self.self_thread.start()


class Client:
    """The Client class. It holds a client socket and integrates with threading to make life easier."""
    
    def __init__(self, addr : tuple[str, int] = None, timeout : int = 5, reuse_addr : bool = True, connect_callback : Callable[[socket.socket, tuple[str, int]], None] = None):
        if not connect_callback:
            connect_callback = lambda server, _: (warning("Connected successfully, but you need to define connect_callback in Client!"), server.close())
        self.addr : tuple[str, int] = addr
        self.timeout : int = timeout
        self.socket : socket.socket = None
        self.reuse_addr : bool = reuse_addr
        self.connect_callback : Callable[[socket.socket, tuple[str, int]], None] = connect_callback

    def find_server(self):
        """The client will find the server using .connect files or UDP broadcasts."""
        connectReturn = get_address_from_file()
        if connectReturn:
            self.addr = connectReturn
            debug("Successfully found .connect file!")
            return
        broadcastReturn = get_address_from_broadcast(timeout=self.timeout)
        if broadcastReturn:
            self.addr = broadcastReturn
            debug("Successfully received UDP broadcasts!")
            return
        raise Exception("Could not find .connect file or UDP broadcasts!")

    def run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        if self.reuse_addr:
           self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.connect(self.addr)
        self.connect_callback(self.socket, self.addr)

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()


def create_connection_file(ip : str, port : int):
    with open("target.connect", "w") as file:
        file.write(f"addr|{ip}\nport|{port}\n")

def main():
    choice = input("Hello! Would you like to create a .connect file? y/n\n").lower()
    if choice == "y":
        ipChoice = input("What IP should I use?\n").strip()
        portChoice = input(f"What port should I use? If you want to use the default port ({PORT}), type d.\n").strip().lower()
        if portChoice == "d":
            portChoice = PORT
        else:
            portChoice = int(portChoice)
        create_connection_file(ipChoice, portChoice)

if __name__ == "__main__":
    main()




