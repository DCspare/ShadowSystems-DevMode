📂 Phase 2 Blueprint: Telegram Ecosystem & Bots<br>
> **Filename:** `docs/v2_blueprint/context_03_telegram_logic.md`<br>
**Role:** Application Logic, Content Ingestion, User Management, and "Swarm" Coordination.<br>
**Technology:** Python 3.10+, Pyrogram (MTProto), asyncio, Motor (MongoDB), Redis.

---

## 🐝 1. Architecture: The "Hive" Model

We strictly separate **Administrative Logic** from **Heavy Transfer Logic** to prevent cascading bans.

### Service A: The Manager Bot (The Brain)
*   **Role:** Single point of contact for Admin and Web Frontend. It *never* downloads files. It manages data and commands.
*   **Identity:** `StreamVaultBot` (Public, branded).
*   **Infrastructure:** Runs in the `manager-api` container (shared with FastAPI).

### Service B: The Worker Swarm (The Muscle)
*   **Role:** 10+ Rotating Physical SIM accounts. They perform the heavy downloads, uploads, and streaming.
*   **Identity:** `Worker1`, `Worker2`... (Private, invisible to users).
*   **Infrastructure:** Runs in the `worker-hive` container as parallel `asyncio` tasks.

---

## 🤖 2. The Manager Bot Features

### 🔐 Auth & Compliance
- [ ] **Auth Token Generator (Magic Link)**
  Generates anonymized `jwt_token` links (`streamvault.net/auth?token=...`) that allow the website to adopt the Telegram User ID for "Premium" status without the user logging in directly.
- [ ] **Global Kill Switch (`/takedown`)**
  Executes the abuse protocol: instantly wipes specific content ID from MongoDB, triggers Nginx Cache Purge on host, and deletes the source message in Telegram.
- [ ] **User Gatekeeper**
  Validates User Permissions (Free/Premium/Banned) and enforces rate limits before signing secure stream URLs for the Frontend.
*   **Secure Link Signer:**
    *   **Action:** When a user requests to play a video (StreamVault server), the API must append Nginx parameters.
    *   **Logic:** Generate `?md5={hash}&expires={timestamp}` using the `SECURE_LINK_SECRET`.
    *   **Expiry:** Set links to expire in +4 hours (enough for a movie length + pause time).
*   **Hashing Algo Strictness:**
        *   Must use Python `hashlib.md5`.
        *   **CRITICAL:** The Base64 output must be **URL-Safe** and **Unpadded**.
        *   *Python Logic:* `base64.urlsafe_b64encode(hash).decode('utf-8').replace('=', '')`
        *   *Why:* Nginx expects this specific format. Standard Base64 will cause 403 Forbidden errors.

### 📚 Content Management
- [ ] **Metadata "Hoarder"**
  Silent proxy that queries TMDB/OMDB API for Posters/Plots and caches them to MongoDB. *Decouples Frontend from public APIs.*
- [ ] **Direct Forward Indexing**
  Instantly processes files "Forwarded" from other Telegram channels without re-uploading (Cloning), mapping existing File IDs to new Database Entries.
- [ ] **Broken Link "Medic"**
  Receives User/Frontend "Dead Link" reports, checks HTTP Head validity, and triggers the Re-Leech queue if the file is truly gone.
- [ ] **Manual Override Console**
  `/edit [TMDB_ID]` command allows manual Admin correction of bad metadata matches or replacing cover art directly from chat.
- [ ] **Slug Generator Service**
  *   **Logic:** Upon new content ingestion, generates a unique 7-character random string (`[a-zA-Z0-9]`).
  *   **Collision Handling:** Performs a recursive check against MongoDB to ensure the slug doesn't already exist.
  *   **Migration Tool:** Command `/fix_slugs` that generates short IDs for all existing legacy content in the DB.

### 📢 Growth & Revenue
- [ ] **Referral Engine (Viral Loop)**
  Tracks unique invite links (`/start?ref=123`). Validates "New User" criteria (to prevent self-invite cheating) and auto-rewards the inviter with "7-Day 4K Premium" status upon hitting quotas.
- [ ] **Broadcast Publisher**
  Auto-posts "New Release Cards" (Poster + Website Link) to the **Public Update Channel** immediately after ingestion.
- [ ] **Ad-Link Generator**
  Integrates URL Shortener APIs (e.g., GPlinks) to tokenize downloads for heavy files (Season Packs), creating valid Access Cookies for the web.
- [ ] **Wishlist Notifier**
  Tracks user requests (`/request Movie`) and automatically DMs them when the requested content is added to the library.
- [ ] **Ghost Comment Moderator**
  Stateless API module managing the `comments` collection.
  *   **Word Filter:** Reject submission if regex matches racial slurs or spam domains.
  *   **Logic:** Stores comments in MongoDB (independent of Telegram), allowing smooth migration from Phase 1 (Hugging Face) to Phase 2 (Oracle) without data loss.

### 📊 Admin Analytics
- [ ] **Daily Stat Reporter**
  Scheduled cron job that sends a summary to the Admin Private Channel at 12:00 AM:
  *   Total New Users
  *   Total Bandwidth Consumed (Oracle)
  *   Number of Dead Links Fixed
  *   Storage Used (Cache %)
- [ ] **The "Sheriff" (Subscription Enforcer)**
  A Daily Cron Job (`00:00 UTC`) that scans the `tenants` collection.
  *   **Logic:** If `today > next_bill_date`:
      *   1. Mark `status: past_due`.
      *   2. Send Notification to Owner (Email/Telegram).
      *   3. Grace Period Check: If > 3 days late -> Set `status: suspended` (Site shows "Maintenance Page").
  *   **Stats Rollup:** Also aggregates Daily Traffic counters from Redis into the Tenant's `stats.monthly_visitors` field for the month-end report.

---

## 🚜 3. The Worker Bot Features (Leech & Stream)

### 📥 Ingestion & Mirroring
- [ ] **Dual-Path Ingestion**
  Processes files via two simultaneous logic paths:
  1.  **Stream Path:** Extracts video for streaming.
  2.  **Zip Path:** Creates a `.7z` archive (no compression) for "Season Packs" upload.
    
- [ ] **Crowdsourced Ingestion Engine**
  Public mode accepting user links/torrents into a "Quarantine/Dump Channel". Files remain pending until Admin clicks "Approve".
*   **Optimization Rule (Zero-Bandwidth Forwarding):**
        *   When delivering the file to the user's DM (after upload to Log Channel), the bot **MUST** use the Telegram `send_document(file_id=...)` method using the generated File ID.
        *   **Constraint:** Do NOT re-upload the file bytes to the user. This ensures 0% bandwidth usage for the delivery leg.
    
- [ ] **Manual Cache Health Probe (`/health`)**
  *   **Feature:** Command listener handles `/health` trigger from Log Channel.
  *   **Logic:** Upon receiving the message, Pyrogram internally captures and caches the Channel's Access Hash.
  *   **Usage:** Mandatory manual step if a worker gets "Peer ID Invalid" errors on a fresh container deployment.

- [ ] **"Ani-Cli" Fallback Scraper**
  *   **Integration:** Worker container includes the `ani-cli` bash script (cloned from repo).
  *   **Usage:** If `yt-dlp` fails on specific Anime Sites (Gogo/Zoro), the Worker executes `ani-cli -e -q 1080 <query>` to extract the raw `.m3u8` stream link.
*   **Command Pattern:**
`ani-cli --no-detach --quality best --episode 5 "One Piece"`
    *   `--no-detach`: Keeps the process attached so Python can read the output.
    *   `--quality best`: Skips the quality selection menu.
  *   **Pipeline:**
      1.  Ani-Cli gets the Master URL.
      2.  Passes URL to `aria2c` or `ffmpeg`.
      3.  File downloaded -> Uploaded to Telegram.
    
- [ ] **Multi-Source Mirroring**
  Simultaneously uploads copies to Backup Hosts (Abyss.to / StreamWish) to create a RAID-1 redundancy layer in case of Telegram bans.
*   **Resource Note:** Cloning to a Backup Mirror (Abyss.to) consumes **2x Outbound Bandwidth** (1x to Telegram + 1x to Backup).
    *   **Stream Cloning:** Implementation must use `io.TeeReader` or Python's equivalent to pipe the *same* download stream to both destinations simultaneously (to keep RAM usage low).
*   **Traffic Management Rule (Daisy Chaining):**
        *   **Direct Uploads:** Limit concurrent direct uploads to **Telegram** and **One High-Speed Mirror** (e.g., PixelDrain) only.
        *   **Remote Uploads:** For secondary backups (Abyss/StreamWish), use their **Remote Upload API** by passing the generated PixelDrain URL.
        *   **Goal:** Minimizes VPS outbound bandwidth usage to max 2x the file size.
*   **The "Shadow Mirror" (Channel Backup):**
        *   **Config:** Requires a secondary `TG_BACKUP_CHANNEL_ID`.
        *   **Action:** Immediately after uploading to the Main Log Channel, the bot **Forwards** the message to the Backup Channel.
        *   **Why:** Ensures that if the Main Channel is banned by Telegram, the file integrity survives in the backup location (Zero bandwidth cost).

**Multi-Hoster Mirroring**
- [ ] **Multi-Up Strategy (Download Mirrors):**
  *   **Logic:** Worker maintains API integrations for **PixelDrain** and **Gofile** (as they allow anonymous API uploads).
  *   **HubCloud/Drive:** If we support these, use "Remote Upload" via the PixelDrain link to populate them without burning bandwidth.
  *   **Storage:** Store ALL returned URLs in the `downloads` array for the Archive Page.
    
- [ ] **Smart Renaming Engine**
  Standardizes filenames (PTN Parser) to remove spam tags (`[x265]`, `www.site.com`) and injects "StreamVault" branding before upload.
> **Aria2 Daemon Logic:** The Python Worker `main.py` must perform a "Cold Start" of the Aria2 binary using `subprocess` with specific flags: `--enable-rpc --rpc-listen-all=false --rpc-allow-origin-all` before the worker loop begins.

- [ ] **Embed-Host Daisy Chaining:**
  *   **Workflow:**
      1.  Worker uploads to **PixelDrain** (Primary File Host).
      2.  Manager Bot takes the PixelDrain URL.
      3.  Manager sends "Remote Upload" commands to **VidHide**, **StreamTape**, and **FileLions** APIs.
  *   **Result:** The files propagate to 3 different streaming hosts using *their* bandwidth, not yours.
  *   **Storage:** Saves the generated Iframe URLs to the Database.

### 🗄️ Archive Capabilities (Rclone Integration)
- [ ] **The "Cloud Bridge":**
  *   Worker container includes `rclone` binary.
  *   **Capabilities:** Can push downloaded files to any supported Rclone provider (Mega/Drive/OneDrive) via the Admin Panel command.
  *   **Configuration:** Reads `rclone.conf` generated dynamically by the Manager Bot (Admin uploads config -> Manager saves to volume -> Worker reads volume).

### 🎞️ Processing Logic
- [ ] **Subtitle Stream Prober**
  Analyzes input files with `ffprobe` to map embedded subtitle tracks (Eng, Spa, Fre) indices (`0:3`, `0:4`) so the Web Player can extract them on-demand.
- [ ] **Auto-Screenshot Extraction**
  Extracts 3-5 frames during the download process using FFmpeg and hosts them on a private channel for the Website's "Quality Preview" gallery.
- [ ] **Proxy/Network Tunneller**
  Configurable SOCKS5 support (`pyrogram[socks]`) allowing specific workers to route traffic through proxies to bypass ISP blocks on torrent trackers.
- [ ] **Sample Clip Generator (Quality Check)**
  *   **Feature:** Automatically generates a 30-second video sample from timestamp `00:10:00` (skips intro black screens).
  *   **Method:** Uses `ffmpeg -ss ... -t 30 ... -c:v libx264 -preset ultrafast` to create a lightweight preview.
  *   **Delivery:** Uploads the Sample alongside the Main Video and Caption as a **Telegram Media Group (Album)** so logs look clean.
  *   **Config:** Toggle via `GENERATE_SAMPLES=true` in environment.

### ⚖️ Load Management
- [ ] **Swarm Rotation Logic**
  Redis-backed algorithm that distributes tasks to the "Least Busy" worker session. Prevents Flood Wait bans by spreading 1,000 requests across 10 accounts.
- [ ] **Queue System**
  Limits concurrent heavy tasks (e.g., Unzipping/Mirroring) to ~5 active threads to protect the Oracle VPS CPU.

---

## 💾 4. Data Strategy & Channels

### Channel Hierarchy (Buckets)
- **Channel A: Public Updates** (Safe. Clean. Links only to Website. No files.)
- **Channel B: Private Logs** (Storage of verified Videos & Images. Segmented by Genre: Action, Horror, etc.)
- **Channel C: Dump/Quarantine** (Holding area for Crowdsourced User uploads).
- **Channel D: Admin Alerts** (System Health, DMCA Reports, Login notifications).

### Safety Features
- **Hash-Based Blocking:** Ingestion phase calculates file hash; cross-references against `global_blocklist` (CSAM/Illegal) before upload.
- **Identity Isolation:** Worker API Keys/Hashes are separate from Manager keys. A ban on a worker does not affect the Manager's ability to chat with users.

---
