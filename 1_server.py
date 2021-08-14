import socket
import threading
from threading import Thread
import atexit
from os import listdir
from os import stat
from os.path import isfile, join
import time
SERVER_PORT = 9016


def exit_handler():
    s.close()


def split_bin(dat, mark):
    result = []
    current = ''
    for i in range(len(dat)//1024):
        block = dat[i*1024:min((i+1)*1024, len(dat))]
        current += block
        while 1:
            markerpos = current.find(mark)
            if markerpos == -1:
                break
            result.append(current[:markerpos])
            current = current[markerpos + len(mark):]
    result.append(current)
    return result

class s_thread(Thread):
    """
    Extends Thread class
    One thread for each connecected client
    """
    def __init__(self, client_id, sock, c, addr, clients, *args, **kwargs):
        self.client_id = client_id
        self.sock = sock
        self.c = c
        self.addr = addr
        self.clients = clients
        super(s_thread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        while True:
            rd = c.recv(5000)
            try:
                if rd[:len("POST /file_upload_parser HTTP/1.1")] == b"POST /file_upload_parser HTTP/1.1": raise UnicodeError
                rd = rd.decode()
                break
            except UnicodeError:
                # case upload
                if rd[:len("POST /file_upload_parser HTTP/1.1")] == b"POST /file_upload_parser HTTP/1.1":
                    boundary = rd.split(b'; boundary=', 1)[1].split(b'\r\n')[0]
                    tmp = rd.split(boundary, 3)
                    # For large files: fo buffering and check for boundary
                    if len(tmp) < 4:
                        buf = c.recv(100000)
                        rd += buf
                        tmp = rd.split(boundary, 3)
                        while len(tmp) < 4:
                            buf = c.recv(100000)
                            rd += buf
                            tmp = rd.split(boundary, 3)
                    tmp1 = tmp[2].split(b'filename="', 1)[1]
                    tmp2 = tmp1.split(b'"\r\n', 1)
                    fl_name = tmp2[0].decode('utf-8')
                    cont = tmp2[1].split(b'\r\n\r\n', 1)[1][:-4]
                    with open(join("public", "data", fl_name), "wb") as f:
                        f.write(cont)
                    # send success
                    data = "HTTP/1.1 201 OK\r\n"
                    data += "Content-Type: text/html; charset=utf-8\r\n"
                    data += "Location: /\r\n"
                    data += "\r\n"
                    data += "<h4> Upload completed Succesfully!</h4>"
                    data += "\r\n\r\n"
                    c.sendall(data.encode())
                    c.shutdown(socket.SHUT_WR)
                    print('New file uploaded and connection closed: ', addr, 'Client ID: ', c_id)
                    return None
                continue
        print('New data: ', rd[:50], ['...', ''][len(rd)<50])
        pieces = rd.split("\n")
        print('New connection: ', addr, 'Client ID: ', c_id)
        if len(pieces) > 0:
            print('client: ', pieces[0][:50], ['...', ''][len(pieces[0][:50])<50], '\n')
            if pieces[0][:len("GET / HTTP/1.1\r")] == "GET / HTTP/1.1\r":
                data = "HTTP/1.1 200 OK\r\n"
                data += "Content-Type: text/html; charset=utf-8\r\n"
                data += "\r\n"
                with open("public/index1.html", "r") as f:
                    data += "".join(f.readlines())
                dfiles = [f for f in listdir(join("public", "data")) if isfile(join("public", "data", f))]
                dfiles.sort()
                for i in dfiles:
                    url = "file/" + i
                    data += "<li class=\"list-group-item\"><strong>" + i + "</strong>"
                    if stat(join("public", "data", i)).st_size < 1024:
                        data += " (" + str(stat(join("public", "data", i)).st_size) + " Bytes, "
                    elif stat(join("public", "data", i)).st_size < 1024 * 1024:
                        data += " (" + str(stat(join("public", "data", i)).st_size//1024) + " KB, "
                    else:
                        data += " (" + str(stat(join("public", "data", i)).st_size//1048576) + " MB, "
                    data += "Last modified: " + str(time.strftime('%H:%M:%S %d-%m-%Y', time.localtime(stat(join("public", "data", i)).st_mtime))) + " ) "
                    data += "<input class=\"btn btn-default\" type=\"button\" value=\"Download\" " \
                            "onclick=\"window.open('" + url + "', '_blank');\"> "
                    data += "</li>"
                with open("public/index2.html", "r") as f:
                    data += "".join(f.readlines())
                data += "\r\n\r\n"
                c.sendall(data.encode())
            elif pieces[0][:len("GET /style.css HTTP/1.1\r")] == "GET /style.css HTTP/1.1\r":
                data = "HTTP/1.1 200 OK\r\n"
                data += "Content-Type: text/css; charset=utf-8\r\n"
                data += "\r\n"
                with open("public/style.css", "r") as f:
                    data += "".join(f.readlines())
                data += "\r\n\r\n"
                c.sendall(data.encode())
            elif pieces[0][:10] == "GET /file/file_name"[:10]:
                data = b"HTTP/1.1 200 OK\r\n"
                data += b"Content-Type: application/octet-stream;\r\n"
                data += b"\r\n"
                fname = pieces[0][10:].split(' HTTP/1.1', 1)[0]
                try:
                    with open(join("public", "data", fname), "rb") as f:
                        data += f.read()
                except FileNotFoundError:
                    print('Error from client: File not found on server')
                data += b""
                c.sendall(data)
        c.shutdown(socket.SHUT_WR)
        print('connection closed: ', addr, 'Client ID: ', c_id)


if __name__ == '__main__':
    atexit.register(exit_handler)
    host = '0.0.0.0'
    port = SERVER_PORT
    clients = {}
    c_id = 1
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    print('Server Started on port ' + str(SERVER_PORT) + '\n(use ifconfig to find IP of this machine. And use http not https)')
    while True:
        c, addr = s.accept()
        rcv_thread = s_thread(client_id=c_id, sock=s, c=c, addr=addr, clients=clients)
        clients[c_id] = rcv_thread
        rcv_thread.start()
        c_id += 1

