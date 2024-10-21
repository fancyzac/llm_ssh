
import paramiko
import socket
import threading
import requests
import re  

class MySSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip, username=None, password=None):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.username = username
        self.password = password

    def check_auth_password(self, username, password):
        if self.username and self.password:
            if username == self.username and password == self.password:
                return paramiko.AUTH_SUCCESSFUL
            else:
                return paramiko.AUTH_FAILED
        return paramiko.AUTH_SUCCESSFUL  

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
    
    def check_channel_exec_request(self, channel, command):
        command = str(command)
        return True


# Emulated Shell
def emulated_shell(channel,timeout_event,log_obj):
    prompt = b'root@server:~# '  # Default prompt
    channel.send(prompt)  # Send the initial prompt
    command = b""
    
    

    while True:
        char = channel.recv(1)  # Read input character-by-character
        channel.send(char)  # Echo back the character to the client

        if not char:
            channel.close()
            return
        
        # Detect back
        # space (usually '\x7f')
        if char == b'\x08' or char == b'\x7f':  # Backspace or Delete
            if len(command) > 0:
                # Remove last character from command
                command = command[:-1]
                # Move cursor back, clear character, move cursor back again
                channel.send(b'\x08 \x08')  
            continue  # Skip further processing for backspace

        timeout_event.set()
        command += char
        
        # command handler
        if char == b'\r':  # When Enter key is pressed
            command = command.strip()
            log_obj.log("SSH Session: Receive command:{}".format(command.decode()))

            if command == b'exit':
                response = b'\r\nGoodbye!\r\n'
                channel.send(response)
                channel.close()
                return
            
            elif command == b'':  # Empty command (just Enter pressed)
                response = b'\r\n'
            else:
                url = "http://127.0.0.1:12345/execute"
                params = {"command": command}
                response_text = requests.get(url, params=params).text.strip()

                if not response_text:
                    response_text = "bash: {}: command not found.".format(command.decode())
                    

                response = format_for_terminal(response_text).encode('utf-8')
                
            log_obj.log("SSH Session: Response:{}".format(response.decode()))
            # Ensure proper newlines before the response
            channel.send(b'\r\n' + response + b'\r\n')  # Send the response
            channel.send(prompt)  # Send the prompt for the next command
            command = b""
    channel.close()

def format_for_terminal(response_text):
    """
    Function to format the response text with proper spacing and newlines
    for terminal output. Adjusts tab spaces, line breaks, etc.
    """
    # Step 1: Replace tabs with spaces for proper alignment
    response_text = response_text.replace("\t", "    ")

    # Step 2: Remove 'plaintext' markers and any dots (...)
    response_text = re.sub(r'\bplaintext\b', '', response_text)  # Remove 'plaintext'
    response_text = re.sub(r'\.{2,}', '', response_text)  # Remove multiple dots (e.g., '...')
    # Remove backticks (```)
    response_text = re.sub(r'[`]', '', response_text)  # Remove backticks

    # Step 3: Ensure proper newline endings consistent with terminal output
    response_text = response_text.replace("\n", "\r\n")

    return response_text

def log_with_format(self, message, level="info"):
    formatted_message = "SSH Session info: {}".format(message)
    self.log_obj.log(formatted_message, level)
