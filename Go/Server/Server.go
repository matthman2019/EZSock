package main

import (
	"net"
	"github.com/matthman2019/EZSock/Go"
)

var sendMap = map[string]any{
	"title": "Hello There!",
}

func ServerCallback(conn net.Conn, addr string) {
	ezsock.SendOnSock(conn, sendMap)
	conn.Close()
}

func main() {
	s := ezsock.Server{Addr:ezsock.IPTuple{IP:"0.0.0.0", Port:ezsock.PORT}, ServerCallback:ServerCallback}
	s.Run()
}
