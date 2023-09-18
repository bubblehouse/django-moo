from abc import ABC, abstractmethod
from sys import platform
import socket
import threading

import paramiko

from . import repl

class ServerBase(ABC):
    def __init__(self):
        self._is_running = threading.Event()
        self._socket = None
        self.client_shell = None
        self._listen_thread = None

    def start(self, address='127.0.0.1', port=8022, timeout=1):
        if not self._is_running.is_set():
            self._is_running.set()

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

            if platform == "linux" or platform == "linux2":
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)

            self._socket.settimeout(timeout)
            self._socket.bind((address, port))

            self._listen_thread = threading.Thread(target=self._listen)
            self._listen_thread.start()

    def stop(self):
        if self._is_running.is_set():
            self._is_running.clear()
            self._listen_thread.join()
            self._socket.close()

    def _listen(self):
        """
        The listen() function will constantly run if the server is running.

        We wait for a connection, if a connection is made, we will call our abstract connection_function()
        function, which will be implemented inside of our specific server class, described later on. Note
        that we wrap the code in this function in a try, except statement. This is because we expect
        self._socket.accept() to break if the server is stopped
        """
        while self._is_running.is_set():
            try:
                self._socket.listen()
                client, addr = self._socket.accept()
                self.connection_function(client)
            except socket.timeout:
                pass

    @abstractmethod
    def connection_function(self, client):
        pass

class SshServerInterface(paramiko.ServerInterface):
    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        return True

    def check_auth_password(self, username, password):
        if (username == "admin") and (password == "password"):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_banner(self):
        return ('Termiverse SSH Server\r\n', 'en-US')

class SshServer(ServerBase):
    def __init__(self, host_key_file, host_key_file_password=None):
        super(SshServer, self).__init__()
        self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)

    def connection_function(self, client):
        try:
            session = paramiko.Transport(client)
            session.add_server_key(self._host_key)

            server = SshServerInterface()
            try:
                session.start_server(server=server)
            except paramiko.SSHException:
                return

            channel = session.accept()
            stdio = channel.makefile('rwU')

            self.client_shell = repl.REPL(stdio, stdio)
            self.client_shell.cmdloop()

            session.close()
        except:
            pass
