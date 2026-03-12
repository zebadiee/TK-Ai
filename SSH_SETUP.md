# SSH Cluster Connectivity Setup

## Status: ✅ ACTIVE

SSH tunnel from ATLAS to HADES is established and fully operational.

---

## Connection Details

| Node | Hostname | IP | SSH Port | Status |
|------|----------|-----|----------|--------|
| **ATLAS** | atlas | 192.168.1.17 | 22 | ✅ Local |
| **HADES** | hades | 192.168.1.12 | 22 | ✅ Connected |
| **HERMES** | hermes | 192.168.1.12 | 22 | 🔄 Secondary |

---

## Setup Pathway Used

### 1. Network Reachability
```bash
ping -c 3 192.168.1.12
# Result: 3 packets transmitted, 3 received, 0% packet loss
```

### 2. SSH Port Availability
```bash
nc -zv 192.168.1.12 22
# Result: Connection to 192.168.1.12 22 port [tcp/ssh] succeeded!
```

### 3. SSH Key Generation
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -C "atlas@tk-ai-cluster"
# Generated: /home/zebadiee/.ssh/id_rsa (private)
# Generated: /home/zebadiee/.ssh/id_rsa.pub (public)
```

### 4. Key Exchange
```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub zebadiee@192.168.1.12
# Status: Keys already present (connection pre-configured)
```

### 5. Verify Connection
```bash
ssh zebadiee@192.168.1.12 "hostname && uptime"
# hades
#  17:12:53 up 50 days, 23:42, 1 user, load average: 0.02, 0.03, 0.03
```

---

## Cluster Health from HADES

```
=== TK-AI CLUSTER DOCTOR ===

Node: hades

Cluster nodes:
 - hades (control)
 - atlas (gpu_worker)
 - hermes (gateway)

--- NETWORK CHECK ---
ATLAS TCP 11434: OK

--- OLLAMA CHECK ---
Ollama API: OK

--- PIPELINE ---
Signals file: OK
Evidence file: OK
Investigation daemon: active

--- ROUTER STATUS ---
Router chain: http://192.168.1.17:11434 -> http://hermes:11434 -> http://localhost:11434

--- LOCAL HOST ---
Hostname: hades
IP: 127.0.1.1
```

---

## SSH Command Reference

### Connect to HADES
```bash
ssh zebadiee@192.168.1.12
```

### Run command on HADES (no prompt)
```bash
ssh zebadiee@192.168.1.12 "command_here"
```

### Copy files to HADES
```bash
scp ~/file.txt zebadiee@192.168.1.12:~/
```

### Copy files from HADES
```bash
scp zebadiee@192.168.1.12:~/file.txt ~/
```

### SSH tunnel for port forwarding
```bash
ssh -L 11434:192.168.1.17:11434 zebadiee@192.168.1.12
# Access ATLAS Ollama locally via http://localhost:11434
```

---

## Key Features

✅ **Passwordless SSH** — RSA key authentication enabled
✅ **Bidirectional communication** — ATLAS ↔ HADES working
✅ **Cluster inference** — ATLAS Ollama reachable from HADES
✅ **Evidence pipeline** — Signals analyzed and stored
✅ **Persistent daemon** — Investigation service active

---

## Next Steps

1. **Test multi-stage investigations** from HADES
   ```bash
   ssh zebadiee@192.168.1.12 "cd ~/TK-Ai-Maxx && PYTHONPATH=. python3 tools/tkai_investigation_daemon.py --once"
   ```

2. **Monitor evidence in real-time**
   ```bash
   ssh zebadiee@192.168.1.12 "tail -f ~/TK-Ai-Maxx/vault/evidence/evidence.jsonl"
   ```

3. **Check daemon status**
   ```bash
   ssh zebadiee@192.168.1.12 "systemctl --user status tkai-investigation"
   ```

---

## Troubleshooting

If SSH connection fails, verify:

```bash
# Check SSH running on HADES
ssh zebadiee@192.168.1.12 "sudo systemctl status ssh"

# Check firewall allows port 22
ssh zebadiee@192.168.1.12 "sudo ufw allow 22/tcp"

# Verify key on HADES
ssh zebadiee@192.168.1.12 "cat ~/.ssh/authorized_keys | grep atlas@"
```

---

## Architecture

```
ATLAS (GPU node)
    └─ Ollama inference (mistral, llama3, qwen, etc.)
         │
         │ HTTP (port 11434)
         │
    HADES (Control plane)
    └─ Signal ingestion
    └─ Investigation engine
    └─ Evidence ledger
    └─ ClawX reasoning
         │
         └─ Policy decisions → Scheduler
```
