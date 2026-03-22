package main
import "github.com/matthman2019/EZSock/Go"

import "fmt"
import "net"
import "time"

func ClientCallback(conn net.Conn, addr string) {
	recvStr, err := ezsock.ReceiveOnSock(conn)
	if err != nil {
		panic(err)
	}
	fmt.Println(recvStr)
}

func main() {
	client := ezsock.Client{Client_callback: ClientCallback}
	client.FindServer()
	client.Start()
	fmt.Println("Yo bro")
	time.Sleep(5 * time.Millisecond)
	fmt.Println("Ok")
}
