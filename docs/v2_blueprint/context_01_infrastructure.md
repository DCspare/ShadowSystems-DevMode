> 📂 Phase 2 Blueprint: Infrastructure & Backend<br>
**Filename:** `docs/v2_blueprint/context_01_infrastructure.md`<br>
**Role:** The "Engine Room" (Oracle A1 VPS + Docker Swarm)

---

## 🏛️ 1. Architecture Overview (The Swarm)

We utilize the Oracle **Ampere A1 (ARM64)** instance as a single-node microservices cluster orchestrated via **Docker Compose**.

### The Service Map
The system runs as isolated containers communicating on an internal bridge network (`streamvault-internal`).

| Service Name | Image Base | Role | Key Dependencies | RAM |
| :--- | :--- | :--- | :--- | :--- |
| **`gateway`** | `nginx:alpine` | **Edge Router.** SSL, Reverse Proxy, Slice Caching, Guest Throttling. | `nginx-module-vts` | 2.5 GB |
| **`manager-api`** | `python:3.10` | **The Brain.** FastAPI. Auth (Guest/JWT), Database logic, Ad-Link validation. | `motor`, `pyjwt` | 1.0 GB |
| **`stream-engine`** | `golang:1.21` | **The Muscle.** Byte-Streaming, **Subtitle Extraction**. | `ffmpeg`, `ffprobe` | 4.0 GB |
| **`worker-hive`** | `python:3.10` | **The Labor.** 10+ Pyrogram Clients. Ingestion, Zipping, Mirroring. | `ffmpeg`, `7zip` | 3.0 GB |
| **`frontend-ui`** | `node:20` | **The Face.** Next.js SSR Application (Self-Hosted). | `sharp` (Img Opt) | 1.5 GB |
| **`db-mongo`** | `mongo:6` | **Cold Data.** Metadata, Logs. | - | 2.0 GB |
| **`db-redis`** | `redis:alpine` | **Hot Data.** Sessions, Queues, IP Locks. | - | 1.0 GB |
| **`monitor`** | `prom/grafana`| **The Cockpit.** Health Dashboard. | - | 0.5 GB |
| **Host OS** | Ubuntu 22/24 | System Overhead. | - | ~4.0 GB |

### 📶 Swarm Network (IPv6 Rotation)
*   **The Trap:** 10 Bots using 1 IPv4 address looks like a spam farm to Telegram.
*   **The Oracle Fix:** Enable `/64` IPv6 CIDR Block in VCN.
*   **Docker Config:** 
    *   Set `enable-ipv6: true` in `daemon.json`.
    *   Compose Service `worker-video` uses `deploy: replicas: 10`.
    *   Network Config `ipv6_address: auto`.
*   **Result:** Every worker gets a unique Public IPv6. FloodWait risks drops by 90%.
  
---

## 💾 2. The Nginx Smart Cache (Performance Core)

### Storage Configuration
*   **Mount Point:** `/var/lib/oracle/streamvault_cache` (Mapped to `gateway`).
*   **Allocation:** 150GB of the 200GB Host Volume.

### Nginx Logic (`nginx.conf`)
1.  **Slice Module:** Enabled. Videos cached in **10MB chunks** to optimize for seeking/jumping.
2.  **Retention Policy:**
    *   `max_size=150g` (Auto-delete Least Recently Used when full).
    *   `inactive=72h` (Purge content not watched in 3 days).
3.  **Guest Bandwidth Throttling:**
    *   **Guest:** 1.5 MB/s (Cap at ~1080p bitrate).
    *   **Verified:** Unlimited (Max network speed).
4.  **Abuse Purge Hook:**
    *   `location /purge { ... }` (Internal Only). Allows Manager API to physically delete files from disk based on URL Hash during a `/takedown` event.
5.  **Secure Link Protection (Hotlink Defense)**
    *   **Module:** `ngx_http_secure_link_module`.
    *   **Logic:** Endpoints at `/stream/` must contain `?md5=...&expires=...`.
    *   **Validation:** Nginx calculates `md5(SECRET + User_IP + Expiry_Time)`. If mismatched or expired, returns `403 Forbidden` instantly.
    *   *Why:* Prevents other pirate sites from stealing your bandwidth by embedding your Go Engine URL directly.

6.  **Stealth Headers (Fingerprint Removal)**
    *   **Action:** Strip all tech-identifying headers (`Server: nginx`, `X-Powered-By: Next.js`, `X-Runtime: Python`).
    *   **Goal:** Preventing hackers/scanners from identifying exact versions of the tech stack to exploit CVEs.

---

## ⚡ 3. The Backend API & Streaming Engine

### The Manager API (FastAPI)
*   **Auth Routes:**
    *   `/auth/guest`: Fingerprints IP/User-Agent, returns "Guest JWT".
    *   `/auth/telegram`: Verifies Magic Link, returns "Premium JWT".
    *   `/auth/validate-ad`: Verifies callback from URL Shortener (GPlinks) to temporarily unlock "Download" permissions for Guests.
*   **Database Schema:**
    *   **Mongo:** Stores Movie Metadata, File Maps (`{1080p: file_id_1, 720p: file_id_2}`), and Soft Subtitle track lists.
    *   **Redis:** `ip_lock:{token}` (Link Sharing Prevention), `user_concurrency:{id}` (Account Sharing Prevention).

### The Stream Engine (Golang/Python V2)
*   **Passthrough Mode:** Zero-copy streaming from Telegram/Abyss $\to$ Nginx.
*   **Real-Time Processing:**
    *   **Subtitles:** Pipes Telegram stream into `ffmpeg` to extract text streams to WebVTT format on-the-fly (`/stream/{id}/sub.vtt`).
    *   **Zipping:** Pipes multiple Telegram streams into a `zip` stream for Season Packs (`/download/season_pack.zip`).
    *   **Live Remuxing (Middleware):**
        *   Route: `/stream/{id}?mode=remux`
        *   Logic: Detects if a browser cannot play MKV containers. Spawns a lightweight `ffmpeg` process to copy streams (`-c copy`) from MKV to MP4 container in real-time without re-encoding video data (Low CPU).
*   **Failover Logic:** Auto-detects `404/FloodWait` from Telegram and switches source to **Abyss.to** without closing the user connection.

---

## 🔒 4. Networking & Security

### Access Control
*   **Public Access:** ONLY Port `443` (HTTPS) exposed via **Cloudflare DNS Proxy**.
*   **Bot Protection:** **Cloudflare Turnstile** header verification required for all Guest API calls.
*   **Internal Network:** Database ports (`27017`, `6379`) are closed to the outside world; only accessible by `manager-api`.

### Obfuscation (Backend)
*   **Image Proxying:** Backend fetches Telegram images and serves them via `/api/image/{id}` to prevent Ad-blockers/DevTools from seeing `telesco.pe` domains.

---

## 📜 5. Development & Deployment Pipeline

### 🚑 Disaster Recovery (Total System Backup)
*   **Cron Job:** Scheduled task (Daily).
*   **What to Pack:**
    1.  **Database:** `mongodump` of `library` and `users`.
    2.  **Identities:** Zips the `/data/sessions/` folder (Critical Worker Logins).
    3.  **Secrets:** Copies the active `.env` file (Config keys).
*   **Action:** Encrypts zip $\to$ Uploads to `TG_ALERT_CHANNEL`.

### CI/CD Workflow
*   **Tool:** GitHub Actions.
*   **Logic:**
    1.  Push to `main`.
    2.  Runner SSHs into Oracle.
    3.  `git pull origin main`.
    4.  `docker compose up -d --build manager-api` (Hot Reload).

### Dev Environment
*   **VS Code Remote SSH:**
    *   Development happens directly on the Oracle VPS via SSH Tunnel.
    *   Ensures identical environment for FFmpeg/Network testing.

### 🚑 Storage Connectors (Rclone)
We use **Rclone** (CLI Tool) as the universal adapter for cloud storage (Mega, Google Drive, Dropbox), distinct from our "Daisy Chain" streaming setup.

**Rclone vs. Daisy Chain Strategy:**
*   **Daisy Chain (Stream Mirroring):**
    *   *Tool:* API Calls via Manager.
    *   *Target:* VidHide, StreamTape, FileLions.
    *   *Bandwidth Cost:* **$0 (Zero)**. Relies on Remote URL Upload.
    *   *Goal:* Active Streaming Embeds.
*   **Rclone (Backup & Archive):**
    *   *Tool:* `rclone copy` CLI inside containers.
    *   *Target:* Mega.nz, Google Drive (Personal), Backblaze.
    *   *Bandwidth Cost:* **1x Upload**. (Traffic flows Oracle -> Cloud).
    *   *Goal:* Disaster Recovery (Database dumps) and "Cold Storage" of vital files.

**Disaster Protocol:**
*   **Nightly:** Cron runs `mongodump`, zips the Database + Session Files + Env.
*   **Action:** Uses Rclone to push this zip to a secure "Off-Site" cloud (e.g., a free 20GB Mega account).
*   **Recovery:** If Oracle deletes the instance, we pull this zip from Mega to a new server to restore operations instantly.
---
