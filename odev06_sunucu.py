#!/usr/bin/env python3
import datetime
import sys
import threading
import time
import queue
import socket

sockDict = {}
rthreadDict = {}
wthreadDict = {}
logQueue = queue.Queue()


class read_thread(threading.Thread):
    def __init__(self, tName, servSock, dictAddr, wQueue):
        threading.Thread.__init__(self)
        self.servSock = servSock
        self.dictAddr = dictAddr
        self.tName = tName
        self.wQueue = wQueue
        self.login = False
        self.uName = ""
        self.running = True

    def run(self):
        logQueue.put(str(self.tName) + " starting.\n")
        while self.running:
            data = self.servSock.recv(1024)
            self.incoming_parser(data.decode().strip("\n"))
        logQueue.put(str(self.tName) + " exiting.\n")

    def exit(self):
        self.running = False

    def incoming_parser(self, data):
        msg = data.split(" ")
        if not self.login:
            if msg[0] == "\x00":
                pass
            elif msg[0] == "NIC":
                if msg[1]:
                    if not msg[1] in sockDict.keys():
                        sockDict[msg[1]] = self.wQueue
                        del sockDict[self.dictAddr[1]]
                        self.uName = msg[1]
                        logQueue.put(str(self.dictAddr[1]) + " identified themselves as " + str(self.uName) + ".\n")
                        for client in sockDict:
                            if isinstance(client, str):
                                sockDict[client].put("WRN " + self.uName + " kanala geldi.")
                        self.wQueue.put("WEL " + msg[1] + "\n")
                        self.login = True
                    else:
                        self.wQueue.put("REJ " + msg[1] + "\n")
                        logQueue.put(str(self.dictAddr[1]) + " failed to identify themselves.\n")
                        kill_conn(self.servSock, self.dictAddr)
            elif msg[0] == "QUI":
                self.wQueue.put("BYE stranger")
                logQueue.put("Unknown connection " + str(self.dictAddr[1]) + " left.\n")
                kill_conn(self.servSock, self.dictAddr)
            elif msg[0] == "PIN":
                print("Ping.\n")
                self.wQueue.put("PON\n")
            elif msg[0] not in ["NIC", "QUI", "PIN"]:
                self.wQueue.put("LRR\n")

        if self.login:
            if msg[0] == "\x00":
                pass
            elif msg[0] == "NIC":
                # self.wQueue.put("ERR\n") ekstra bi err verio
                pass
            elif msg[0] == "QUI":
                self.wQueue.put("BYE " + self.uName)
                for client in sockDict:
                    if isinstance(client, str):
                        sockDict[client].put("WRN " + self.uName + " kanaldan cikti.")
                kill_conn_user(self.servSock, self.dictAddr, self.uName)
            elif msg[0] == "PIN":
                print("Ping.\n")
                self.wQueue.put("PON\n")
            elif msg[0] == "GLS":
                kul_liste = ""
                for client in sockDict:
                    if isinstance(client, str):
                        kul_liste = kul_liste + str(client) + ":"
                kul_liste = kul_liste[:-1]
                self.wQueue.put("LST " + kul_liste + "\n")
            elif msg[0] == "GNL":
                if msg[1]:
                    gnlmsg = ""
                    for i in range(1, len(msg)):
                        gnlmsg = gnlmsg + str(msg[i]) + " "
                    for client in sockDict:
                        if isinstance(client, str):
                            sockDict[client].put("GNL %s:%s" % (self.uName, str(gnlmsg)))
                    self.wQueue.put("OKG\n")
            elif msg[0] == "PRV":
                splitted = msg[1].split(":")
                if sockDict[splitted[0]]:
                    prvmsg = splitted[1]
                    for i in range(2, len(msg)):
                        prvmsg = prvmsg + str(msg[i]) + " "
                    sockDict[splitted[0]].put("PRV " + self.uName + ":" + str(prvmsg))
                    self.wQueue.put("OKP\n")
                else:
                    self.wQueue.put("NOP\n")
            else:
                # self.wQueue.put("ERR\n")
                pass


class write_thread(threading.Thread):
    def __init__(self, tName, servSock, wQueue):
        threading.Thread.__init__(self)
        self.servSock = servSock
        self.wQueue = wQueue
        self.tName = tName
        self.running = True

    def run(self):
        logQueue.put(str(self.tName) + " starting.\n")
        while self.running:
            data = self.wQueue.get()
            self.servSock.send(data.encode())
        logQueue.put(str(self.tName) + " exiting.\n")

    def exit(self):
        self.running = False


class log_thread(threading.Thread):
    def __init__(self, file_address):
        threading.Thread.__init__(self)
        self.file_address = file_address
        self.running = True

    def run(self):
        while self.running:
            file = open(self.file_address, "a")
            log = logQueue.get()
            file.write(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " : " + log)
            file.close()


def welcome(conn, dictAddr):
    rtn = "read" + str(dictAddr[1])
    wtn = "write" + str(dictAddr[1])
    port_queue = queue.Queue()
    sockDict[dictAddr[1]] = port_queue
    rthreadDict[dictAddr[1]] = read_thread(rtn, conn, dictAddr, port_queue)
    wthreadDict[dictAddr[1]] = write_thread(wtn, conn, port_queue)
    rthreadDict[dictAddr[1]].start()
    wthreadDict[dictAddr[1]].start()


def kill_conn(conn, dictAddr):
    wthreadDict[dictAddr[1]].exit()
    rthreadDict[dictAddr[1]].exit()
    time.sleep(2)
    del rthreadDict[dictAddr[1]]
    del wthreadDict[dictAddr[1]]
    del sockDict[dictAddr[1]]
    time.sleep(2)
    logQueue.put("Connection " + str(dictAddr[1]) + " closed.\n")
    conn.close()


def kill_conn_user(conn, dictAddr, user):
    wthreadDict[dictAddr[1]].exit()
    rthreadDict[dictAddr[1]].exit()
    time.sleep(2)
    del rthreadDict[dictAddr[1]]
    del wthreadDict[dictAddr[1]]
    del sockDict[user]
    time.sleep(2)
    logQueue.put("Connection " + str(dictAddr[1]) + " from user " + str(user) + " closed.\n")
    conn.close()


def main():
    #if not len(sys.argv) == 3:
     #   print("Insufficient parameters. Please run in format python odev06_sunucu.py 0.0.0.0 4430")
      #  return
    logThread = log_thread("log.txt")
    main_socket = socket.socket()
    main_socket.bind(("0.0.0.0", 4430))
    logThread.start()
    main_socket.listen(5)
    while True:
        conn, addr = main_socket.accept()
        logQueue.put("New connection at " + str(addr[1]) + ".\n")
        welcome(conn, addr)


if __name__ == '__main__':
    main()
