from flask import Flask, request
import random
import requests

app = Flask(__name__)

file_system = {
    "/etc/passwd": "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n...",
    "/etc/hostname": "amun-server\n",
    "/var/log/messages": "[2024-01-01 12:00:00] System started\n[2024-01-01 12:05:00] Connection received from 192.168.1.10\n",
    "/home/user/.bashrc": "export PATH=/usr/local/bin:$PATH\nalias ll='ls -la'\n",
    "/home/user/notes.txt": "TODO: Learn Python\nTODO: Write more shell commands\n",
}

# Predefined command responses for Linux and Windows
game_result = {
    "linux": {
        "ls": {"simulated_output": "file1.txt\nfile2.log\nscript.sh\n", "error_message": ""},
        "ifconfig": {
            "simulated_output": """
eth0      Link encap:Ethernet  HWaddr 00:0c:29:68:8c:64  
          inet addr:192.168.1.10  Bcast:192.168.1.255  Mask:255.255.255.0
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:120000 errors:0 dropped:0 overruns:0 frame:0
          TX packets:80000 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:654000000 (654.0 MB)  TX bytes:321000000 (321.0 MB)
        """,
            "error_message": "",
        },
        "nano": {"simulated_output": "", "error_message": "bash: nano: command not found"},
    },
    "windows": {
        "dir": {
            "simulated_output": """
 Volume in drive C has no label.
 Directory of C:\\Windows\\System32

11/22/2024  12:00 PM    <DIR>          .
11/22/2024  12:00 PM    <DIR>          ..
11/22/2024  12:00 PM             1,024 file1.txt
11/22/2024  12:00 PM             2,048 file2.log
            """,
            "error_message": "",
        },
        "ipconfig": {
            "simulated_output": """
Windows IP Configuration

   Ethernet adapter Local Area Connection:

      Connection-specific DNS Suffix  . : example.com
      IPv4 Address. . . . . . . . . . . : 192.168.1.10
      Subnet Mask . . . . . . . . . . . : 255.255.255.0
      Default Gateway . . . . . . . . . : 192.168.1.1
            """,
            "error_message": "",
        },
    },
}

# Command history for context
command_history = {}

# 动态生成 Prompt
def generate_prompt(command, history, system_type, file_system):
    """
    动态生成 Prompt，注入文件系统结构
    """
    history_context = "\n".join([f"$ {cmd}\n{output}" for cmd, output in history.items()]) if history else ""
    file_system_info = "\n".join([f"{path}: {repr(content[:30])}..." for path, content in file_system.items()])

    prompt = f"""
You are a simulated {system_type} shell. Here is the file system structure and contents:
{file_system_info}

Based on the following history:
{history_context}

Execute the following command:
{command}

If the command involves accessing files, use the provided file system data. If the command cannot be executed, respond with appropriate errors like "No such file or directory" or "command not found." Make your output concise and accurate.
"""
    return prompt

# Function to call the LLM for dynamic responses
def get_response_from_llm(command, history=None, system_type="linux"):
    """
    Calls the LLM API for dynamic response generation based on system type.
    - Ensures the response is properly encoded to UTF-8.
    """
    prompt = generate_prompt(command, history, system_type, file_system)
    response = requests.post(
        "https://api.gpts.vin/v1/chat/completions",
        headers={"Authorization": "Bearer sk-OiUqzSnmLNMdv878yw1iAcWeslqE0s1BXoh43yJ7Y3AfFaEb"},
        json={
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": command},
            ],
        },
    )
    if response.status_code != 200:
        print(f"LLM API Error: {response.status_code} - {response.text}")
        return f"LLM API Error: {response.status_code} - {response.text}"

    # Ensure UTF-8 encoding and strip problematic characters
    try:
        result = response.json()["choices"][0]["message"]["content"]
        return result.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    except Exception as e:
        print("Error processing LLM response:", e)
        return "Error processing LLM response"

def detect_system_type(prompt):
    """
    Enhances system type detection based on more comprehensive prompt characteristics.
    """
    if "C:\\WINNT" in prompt or "C:\\Windows" in prompt or "Microsoft" in prompt:
        return "windows"
    elif any(keyword in prompt for keyword in ["#", "~", "/root", "/home"]):
        return "linux"
    else:
        return "unknown"  # Default to unknown if not identified

# Main command handling function
@app.route("/execute", methods=["GET"])
def handle_command():
    """
    Handles incoming command requests and ensures outputs are safe for check_modul.py.
    """
    command = request.args.get("command", "").strip()
    prompt = request.args.get("prompt", "[root@localhost ~]#")  # Default prompt
    system_type = detect_system_type(prompt)  # Detect system type dynamically

    if not command:
        return "Error: No command provided", 400

    strategy = "allow" if random.random() > 0.3 else "error"

    if strategy == "allow":
        output = game_result.get(system_type, {}).get(command, {}).get("simulated_output", "")
        if not output:
            output = get_response_from_llm(command, command_history, system_type)
    else:
        output = game_result.get(system_type, {}).get(command, {}).get("error_message", f"{command}: command not found, maybe try this again")

    # Ensure the output is properly encoded to avoid conflicts
    try:
        output = output.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
    except Exception as e:
        print("Encoding error:", e)
        output = "Error processing command"

    command_history[command] = output
    return output, 200


# Flask application entry point
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=12345)
