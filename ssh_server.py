
import paramiko
import socket
import threading  

class MySSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip, username=None, password=None):
        self.client_ip = client_ip
        self.username = username
        self.password = password

    def check_auth_password(self, username, password):
        if username == "root" and password == "password":
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED
    



def emulated_shell(channel):
    prompt = b'root@server:~# '
    channel.send(prompt)
    command = b""

    while True:
        char = channel.recv(1)
        if not char:
            channel.close()
            return

        command += char
        if char == b'\r':
            command_str = command.strip()
            if command_str == b'exit':
                channel.send(b'Goodbye!\r\n')
                channel.close()
                return

            # Mock response for simplicity
            response_text = "Command received: {}".format(command_str.decode())
            channel.send(response_text.encode('utf-8') + b'\r\n')
            channel.send(prompt)
            command = b""
