package ezsock

import (
	"net"
	"fmt"
	"strconv"
	"os"
	"path/filepath"
	"errors"
	"strings"
	"encoding/json"
	"slices"
	"bytes"
)
const (
	BROADCASTPORT = 56767
	PORT = 26767
)

func TestFunc() {
	conn, err := net.Dial("tcp", "127.0.0.1:26767")
	if err != nil {
		panic(err)
	}
	defer conn.Close()

	buffer := make([]byte, 1024)
	_, errTwo := conn.Read(buffer)
	if errTwo != nil {
		panic(errTwo)
	}
	fmt.Println(string(buffer))
}

func GetLocalIP() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		panic(err)
	}
	defer conn.Close()
	localAddress := conn.LocalAddr().(*net.UDPAddr)
	return localAddress.IP.String()
}

type IPTuple struct {
	IP   string
	Port int
}

func (tuple IPTuple) ToConnectionString() string {
	return tuple.IP + ":" + strconv.Itoa(tuple.Port) 
}

func ServerMulticastDaemon() {
	fmt.Println("There is no server functionality for multicasting yet!")
}

func findConnectFromDir(directory string) (os.DirEntry, error) {
	// start iteration
	files, err := os.ReadDir(directory)
	if err != nil {
		panic(err)
	}
	// iterate through files and find .connect files
	for _, file := range files {
		if file.IsDir() {
			continue
		}
		filename := file.Name()
		suffix := filepath.Ext(filename)
		if suffix == ".connect" {
			return file, nil
		}
	}
	for _, file := range files {
		if !file.IsDir() {
			continue
		}
		findConnectFromDir(file.Name())
	}
	return nil, errors.New("Could not find .connect file!")
}
func GetAddressFromFile() (IPTuple, error) {


	file, err := findConnectFromDir(".")
	if err != nil {
		return IPTuple{}, err
	}
	fileContents, err := os.ReadFile(file.Name())
	lineList := strings.Split(string(fileContents), "\n")
	ip := strings.Split(lineList[0], "|")[1]
	port, err := strconv.Atoi(strings.Split(lineList[1], "|")[1])
	if err != nil {
		panic(err)
	}


	return IPTuple{ip, port}, nil
}

func SendOnSock(sock net.Conn, data map[string]any) error {
	dataBytes, err := json.Marshal(data)
	if err != nil{
		return err
	}
	_, err = sock.Write(dataBytes)
	return err
}
func ReceiveOnSock(sock net.Conn) (map[string]any, error) {
	receivedBuffer := make([]byte, 0)
	buffer := make([]byte, 1024)
	done := false
	finishedMap := make(map[string]any)
	for !done {
		_, err := sock.Read(buffer)
		if err != nil {
			panic(err)
		}
		receivedBuffer = slices.Concat(receivedBuffer, buffer)
		err = json.Unmarshal(bytes.TrimRight(receivedBuffer, "\x00"), &finishedMap)
		if err != nil {
			panic(err)
		} else {
			done = true
			break
		}
	}
	return finishedMap, nil
}

type ServerCallback func(net.Conn, string)

type Server struct {
	Addr IPTuple
	ReuseAddr bool
	Socket net.Listener
	Timeout int
	ServerCallback ServerCallback
}

func (self *Server) Run() {
	// start multicast daemon
	go ServerMulticastDaemon()
	var err error
	self.Socket, err = net.Listen("tcp", self.Addr.ToConnectionString())
	if err != nil {
		panic(err)
	}
	defer self.Socket.Close()
	fmt.Println("Server is up and listening! Address:" + self.Addr.ToConnectionString())
	
	for {
		conn, err := self.Socket.Accept()
		if err != nil {
			fmt.Println("Error receiving connection:", err)
		}
		go self.ServerCallback(conn, conn.RemoteAddr().String())
	}
}

func (self Server) Start() {
	go self.Run()
}

type ClientCallback func(net.Conn, string) 

type Client struct {
	Addr IPTuple
	Timeout int
	Socket net.Conn
	Reuse_addr bool
	Client_callback ClientCallback
}

func (self *Client) FindServer() {
	connectionTuple, err := GetAddressFromFile()
	if err == nil {
		self.Addr = connectionTuple
		return
	}
	// add multicast detection once it can be tested
	// file detection
	panic(errors.New("Could not find .connect file or connect to udp multicast!"))
}

func (self *Client) Run() {
	addrStr := self.Addr.ToConnectionString()
	conn, err := net.Dial("tcp", addrStr)
	if err != nil {
		panic(err)
	}
	self.Socket = conn
	defer self.Socket.Close()
	self.Client_callback(self.Socket, addrStr)
}

func (self Client) Start() {
	go self.Run()
}
