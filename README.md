# 🎬 Shadow Systems: StreamVault + ReadVault (V2)
> **Enterprise-grade streaming backend optimized for Oracle Free Tier (ARM64).**

![Status](https://img.shields.io/badge/Phase-3_Backend_Stable-brightgreen?style=for-the-badge)
![Host](https://img.shields.io/badge/Dev_Env-Google_IDX-orange?style=for-the-badge)
![Database](https://img.shields.io/badge/Storage-Mongo_Atlas-green?style=for-the-badge)
![Bandwidth](https://img.shields.io/badge/Transfer-Telegram_MTProto-cyan?style=for-the-badge)

---

## 📖 The Architecture Path
Following the blueprint defined in **context_01-10**, Shadow Systems utilizes a **Monorepo Architecture**. We treat Telegram as infinite object storage and use an Oracle VPS as a high-speed Nginx Slice-Cache gateway. 

To bypass hardware constraints during building, we utilize **"Potato-Mode" Workflow**, offloading databases to the cloud and simulating the cluster in Google Project IDX.

---

## 📂 Master Directory Structure

```text
SHADOW-SYSTEMS (Root)
├── apps
│   ├── gateway/                  # NGINX Reverse Proxy
│   │   ├── Dockerfile            # Builds the NGINX image
│   │   └── nginx.conf.template   # NGINX configuration template
│   ├── manager/                  # FastAPI Backend (Admin Panel & API)
│   │   ├── core/
│   │   │   ├── __init__.py       # Makes the 'core' directory a Python package
│   │   │   ├── config.md         # (Deprecated)
│   │   │   ├── security.py       # Handles authentication and authorization
│   │   │   └── utils.md          # (Deprecated) Documentation for manager utilities
│   │   ├── handlers/
│   │   │   └── cmd_leech.py      # Contains logic to handle the /leech command from Telegram
│   │   ├── routers/
│   │   │   ├── admin.py          # API endpoints for administration and system stats
│   │   │   ├── auth.py           # API endpoints for user authentication (magic link, guest access)
│   │   │   └── library.py        # API endpoints for searching and managing the media library
│   │   ├── services/
│   │   │   ├── __init__.py       # Makes the 'services' directory a Python package
│   │   │   ├── bot_manager.py    # Manages the Pyrogram client for interacting with Telegram
│   │   │   ├── database.md       # (Deprecated)
│   │   │   └── metadata.py       # Service for fetching metadata from TMDB and other sources
│   │   ├── Dockerfile            # Builds the Docker image for the FastAPI manager application
│   │   ├── main.py               # Main entrypoint for the FastAPI application
│   │   └── requirements.txt      # Lists the Python dependencies for the manager app
│   ├── shared/                   # Shared Python code used by both Manager and Workers
│   │   ├── __init__.py           # Makes the 'shared' directory a Python package
│   │   ├── database.py           # Handles connection to the MongoDB database
│   │   ├── formatter.py          # Logic for creating aesthetically pleasing Telegram message formats
│   │   ├── progress.py           # Calculates and formats download/upload progress and speed
│   │   ├── registry.py           # A state manager for tracking active tasks (downloads, uploads)
│   │   ├── schemas.py            # Pydantic models for data validation and serialization
│   │   ├── settings.py           # Centralized configuration management using Pydantic's BaseSettings
│   │   ├── tg_client.py          # Wrapper for the Telegram client (Pyrogram)
│   │   └── utils.py              # General utility functions shared across applications
│   ├── stream-engine/            # Golang high-performance stream handler
│   │   ├── core/
│   │   │   ├── downloader.go     # Handles the downloading of file chunks from Telegram
│   │   │   └── telegram.go       # Establishes and manages the core connection to Telegram
│   │   ├── Dockerfile            # Builds the Docker image for the Go stream-engine
│   │   ├── go.mod                # Declares the Go module's path and dependencies
│   │   ├── go.sum                # Contains the checksums of the Go module dependencies
│   │   └── main.go               # Main entrypoint for the Go HTTP server that handles streaming
│   ├── worker-video/             # Celery worker for video processing tasks
│   │   ├── handlers/
│   │   │   ├── downloader.py     # Manages the file download process (Aria2/yt-dlp)
│   │   │   ├── flow_ingest.py    # Orchestrates the main workflow: download -> process -> upload
│   │   │   ├── processor.py      # Handles video processing using FFmpeg (screenshots, samples)
│   │   │   └── status_manager.py # Manages and updates the status message on Telegram
│   │   ├── Dockerfile            # Builds the Docker image for the video worker
│   │   ├── entrypoint.sh         # Script that runs on container startup, ensures permissions
│   │   ├── requirements.txt      # Lists the Python dependencies for the video worker
│   │   └── worker.py             # Main entrypoint for the Celery worker, defines the task queue
│   └── web/                      # Frontend application Obsidian Glass UI (Placeholder)
│       └── public/
│           └── js/
│               └── ads_core.js   # Placeholder for client-side advertisement logic
├── config/
│   └── workers/
│       └── prometheus.yml        # Prometheus configuration for monitoring workers
├── data/                         # Local Volume Persistence (Cache/Sessions)
├── docs/                         # Architectural Blueprints (Context Files)
├── .dockerignore
├── .env.example                  # Environmental Secrets
├── .gitignore
├── docker-compose.dev.yml        # Docker Compose file for development environment
├── gen_session.py                # Script for generating a new session
├── README.md                     # Main project documentation
├── sub.txt                       # Example subtitle file
└── Survivors-Log.md              # A log of technical challenges and their solutions
```

---

## 📚 The Documentation Stack (Blueprints)
*Refer to these files in `docs/v2_blueprint/` for the exact code logic.*

| Domain | File Name | Description |
| :--- | :--- | :--- |
| **INFRASTRUCTURE** | [`context_01_infrastructure.md`] | Oracle Swarm, Nginx Cache rules, IPv6 config. |
| **BOT LOGIC** | [`context_02_telegram_logic.md`] | Manager API, Worker Leeching, Mirror logic. |
| **FRONTEND** | [`context_03_frontend_ux.md`] | Next.js Glass UI, Video Player, PWA. |
| **DATABASE** | [`context_04_database.md`] | MongoDB Schemas (Movies, Tenants, Comments). |
| **ROADMAP** | [`context_05_future_roadmap.md`] | Future features: ShadowParty, Stremio, OPDS. |
| **ADMIN** | [`context_06_admin_panel.md`] | The Web Dashboard & Content CMS. |
| **FRANCHISE** | [`context_07_franchise_model.md`] | **SaaS Model**: Pricing, Tenants, Multi-domain logic. |
| **REVENUE** | [`context_08_monetization_ads.md`] | Adsterra, VAST, GPlinks, PPD integration. |
| **SURVIVAL** | [`context_09_growth_survival.md`] | **Defense**: Satellite Config, Bot Warmer, Matrix Log View. |
| **MUSIC** | [`context_11_music_engine.md`] | Extension for Streaming Audio, OSTs, and Background Music. |
| **READVAULT** | [`context_readvault.md`] | **Phase 1-Lite**: Manga architecture for HF Spaces. |

---

## 🛠 Operational Status & Achievements

### 🚀 Phase 1: Infrastructure Baseline (COMPLETED)
- **IDX Environment:** Docker daemon bridged via Nix configuration.
- **Internal Networking:** `sv-internal` bridge connecting Nginx and Manager.
- **Persistence Layer:** Successfully established external connection to **MongoDB Atlas** (Metadata) and **Upstash Redis** (State).
- **Worker-Video Swarm:** ONLINE ✅ (Auth DC5 Handshake Verified)

### 🧠 Phase 2: Core Brain (IN PROGRESS)
- **Ingestion Pipeline:** Redis-Queue (`queue:leech`) connects API to Worker seamlessly.
- **Hybrid Downloader:** Smart fallback system. If `Aria2` fails on Cloud IPs (Error 16), system auto-switches to `yt-dlp` native sockets.
- **Metadata Upsert:** "Skeleton" logic creates database entries even if TMDB fails, preventing file loss.
- **Database Indexing:** Search engine optimized with `title` and `author` Text Indexes.
- **Central Nervous System:** Implemented `apps/shared/settings.py` (Pydantic BaseSettings). Replaced all unsafe `os.getenv` calls with strict type-validated configuration objects, shared across Manager and Workers.

<details>
    <summary><b>🔥 PART 3: Survival, Operations & B2B</b></summary>

- [ ] **"Matrix" Log Streamer**
  Live, color-coded terminal view of all 10 Worker containers streamed via WebSockets to the Admin Panel.
  *Debugging tool to spot "FloodWait" or Leech errors without needing SSH access.*

- [ ] **Visual "ShadowExplorer" (TeleDrive)**
  File Manager UI to view, rename, and thumbnail-fix Telegram files directly from the web.
  *Prevents the "Black Hole" problem of losing files in channels.*

- [ ] **Satellite Connectivity**
  App logic that fetches the API URL from a GitHub raw file if the main domain gets banned.
  *Guarantees zero-downtime recovery for installed PWA users during domain migrations.*

- [ ] **Bot Warmer Incubator**
  Automated script that runs new Worker sessions through a "Human Behavior" pattern (reading/scrolling) for 48h before leeching.
  *The #1 defense against Telegram's ban hammer for new accounts.*

- [ ] **SaaS Franchise Engine (Multi-Tenant)**
  Built-in middleware to support external domains (`client-site.com`) running off your infrastructure for a monthly fee.
  *Turn the platform into a B2B product: You provide the Tech, they bring the Traffic.*
</details>

---

### 🏆 Landmark Achievements (v0.1.0-alpha)
- **[THE GREAT BRIDGE]**: Successfully closed the full-stack loop. Admin `/leech` command -> Redis Queue -> Worker Download -> Telegram Upload -> MongoDB Indexing.
- **[CONTEXT PIERCE]**: Overcame the "Group Context Blindness" hurdle by implementing a manual `/health` ping that force-caches peer hashes.
- **[RESILIENT LEECHING]**: Implemented `File System Wipe` on startup to fix Docker Permission lockups (Error 16).

### 🏆 Achievements (v0.3.0-beta) - The Streaming Engine
- [x] **Smart-Seek Protocol:** Implemented `HTTP Range` headers and **Chunk Alignment Logic** to allow instant seeking to any second of a 4K movie.
- [x] **Identity Cloning:** Configured Go Engine to parse Pyrogram Session Strings, allowing it to "Clone" the Worker's identity and permissions (Zero-OTP login).
- [x] **Peer Persistence:** Replaced RAM storage with **SQLite PeerStorage**, allowing the bot to "Remember" private channel Access Hashes across restarts.
- [x] **Secure Handover:** Validated the Nginx `secure_link_md5` verification and Header Injection pipeline (`X-Location-Msg-ID`) between Python and Go.

- [x] Go-Stream-Engine: Ignition & Concurrency handling skeleton.
- [x] **TARGET DESTROYED:** Go-MTProto Influx (Telegram Bridge & Streaming).
- [x] **TARGET DESTROYED:** Nginx Secure Link & Slice Caching Validation.

### 💎 Achievements (v0.4.0-gamma) - Enrichment & Defense
- [x] **Smart Series Buckets:** Logic to detect `SxxExx` via filename or Manual Hints (`/leech ... "Title S01E01"`) and route files into nested MongoDB Season arrays.
- [x] **FFmpeg Intelligence:** Implemented `processor.py` to probe files for Subtitle languages/Audio Codecs, generate 3 screenshots, and cut 30s sample clips.
- [x] **Aesthetic Logging:** Integrated `formatter.py` to produce clean, tree-styled Telegram captions with metadata pills.
- [x] **Defense Level 1 & 3:** Implemented "Click-to-Sign" Lazy Links (`POST /sign`) and Redis Rate Limiting (5 req/min) to prevent scraping abuse.

### 💎 Achievements (v0.5.0-delta) - The Shared Kernel & Enrichment
- [x] **Architectural Refactor:** Migrated to a **Shared Kernel Pattern (`apps/shared`)**. Database Schemas (`Pydantic`) and Formatter logic are now centralized, preventing code duplication between Manager and Workers.
- [x] **FFmpeg Intelligence:** Integrated `processor.py` to Probe subtitle tracks/audio codecs, generate 3-point screenshots, and cut smart 30s sample clips.
- [x] **Smart Series Mapping:** Logic to detect `SxxExx` via filename or Manual Hints (`/leech ... "Title S01E01"`). Implemented `PTN` logic with a Fallback RegEx to detect `SxxExx` patterns. Episodes now automatically sort into nested MongoDB Season buckets (`seasons.1`, `seasons.2`).
- [x] **Atomic Transactions:** Renamed `leech.py` to `flow_ingest.py` for semantic clarity. Secured the Leech pipeline with "Cleanup-Finally" blocks and strict Database Upsert paths (Skeleton Creation vs Enrichment Update) to prevent data corruption.

### 💎 Achievements (v0.6.0-epsilon) - Identity & Orchestration
- [x] **Stateful Auth Engine:** Implemented JWT-based Guest Identity system with `HttpOnly` cookie security.
- [x] **Granular Data Control:** Added atomic MongoDB `$pull` logic to delete specific files/episodes without nuking the entire title entity.
- [x] **On-the-Fly Subtitle Bridge:** Built a high-performance FFmpeg pipe that extracts "Soft Subtitles" from MKV streams and serves them as `.vtt` to web browsers via an internal header-authenticated Go bridge.
- [x] **Task-UUID Queue Logic:** Upgraded the Redis pipeline to support unique Task IDs, allowing live status tracking and remote "Kill Signals" for specific downloads.

### 💎 Achievements (v0.6.5-alpha) - The Industrial Milestone
- [x] **Shadow Status Registry:** Migrated to a centralized "Registry Pattern." All engines (Download/Upload/Mirror) now report to a global state, enabling a unified UI.
- [x] **MLTB-Standard UI:** Implemented a professional "Heartbeat" loop that updates one single Telegram message every 6 seconds with live CPU/RAM/Disk stats and multi-task progress bars.
- [x] **Smooth EMA Math:** Integrated Exponential Moving Average (EMA) logic for speed calculations, resulting in rock-solid ETA and jitter-free MB/s reporting.
- [x] **Deep-Probe Handshake:** Developed an autonomous peer resolution protocol that force-caches Access Hashes on boot using silent pulses, eliminating the need for manual `/health` commands.
- [x] **Stealth Operational UX:** Implemented "Silent Manager" logic where bot commands triggered in groups are acknowledged in Private DM, and trigger messages are auto-deleted upon task completion to maintain zero clutter.
- [x] **Dynamic Engine Switching:** Automated engine labeling (Aria2 vs YT-DLP) within the Status UI based on link metadata.

### 💎 Achievements (v0.7.0-beta) - Persistence & Protocol
- [x] **Autonomous Handshake Reconstruction**: Bots now utilize "Deep Probing" via MTProto dialog sweeps to rebuild Peer AccessHashes on startup, eliminating the "Manual Message Requirement."
- [x] **Stateful Session Checkpointing**: Implemented Graceful Shutdown (SIGTERM) logic, ensuring the SQLite WAL (Journal) is merged into the permanent `.session` file during container restarts.
- [x] **Hybrid-Identity Node Isolation**: Implemented `WORKER_MODE` protocol. Workers now run in "Stealth-Bot" mode to protect User Identities, while the Manager utilizes "Muscle-User" mode for high-speed metadata ingestion.
- [x] **Unified Logging Kernel**: Standardized logging format across all Python nodes, allowing for clean, time-stamped centralized debugging.

---

## 🏗 System Protocol (The Golden Rules)
1. **The Gateway Wall:** All media requests MUST proxy through the Nginx Gateway; Raw Telegram URLs are never exposed.
2. **Stateless Workers:** Heavy workers must purge temporary data instantly after the Telegram upload phase.
3. **Safety Factor:** Swarm rotation limits any single Telegram session to 15 concurrent users to prevent API bans.
4. **Transience First**: All heavy media processing MUST occur in the container's `/app/downloads/` directory (777 permissions) to ensure global write access.
5. **Task Delegation**: Standard operations (leeches) are triggered via Redis Queues to prevent session lock collisions in the SQLite identity database.

---

## 🏁 Quick Start & Controls

### Booting the Swarm
```bash
docker compose -f docker-compose.dev.yml up -d --build
```

### Monitoring Health
```bash
# Watch the Brain (Manager Bot & DB Connection)
docker logs -f sv-manager-dev

# Watch the Muscle (Worker Downloading Progress)
docker logs -f sv-worker-video-dev
```

### Halting the Engine
```bash
docker compose -f docker-compose.dev.yml down
```

---

## 🛠 The Hurdle Log: Challenges & Resolutions
*The **"Shadow Survivor's Log"**. It documents every technical roadblock we encountered during Phase 1 & 2 in the Google Project IDX environment and the exact "Shadow Protocol" fixes we applied.*
#### 🧱 Hurdle #45: The Ghost Message Persistence
- **The Error:** Status message remains in chat after all tasks are finished.
- **Description:** The loop lacked logic to detect an empty registry and perform self-destruction of the status entity.
- **The Fix:** Implemented a "Master Purge" in the worker's `finally` block and a "Lifecycle Watcher" in the `StatusManager`. The manager now detects `count == 0`, deletes the active status message, and enters a dormant state until a new task is registered.

#### 🧱 Hurdle #46: The MTProto "Cold-Start" Blindness
- **The Error:** `PeerIdInvalid` or `Handshake Fail` until a manual message was sent.
- **Description:** Telegram MTProto clients require an `access_hash` to interact with private peers. This hash was stored in a temporary SQLite Journal (`-wal` or `-journal` files) but was lost during Docker restarts because:
  1. The bot was force-killed (`SIGKILL`) before it could "merge" the journal into the main `.session` file.
  2. A manual script was deleting journal files on startup, essentially wiping the bot's memory of its handshake.
- **The Fix:** 
  1. Implemented **Graceful Signal Handling**: The bots now listen for `SIGTERM` from Docker and call `app.stop()` explicitly, ensuring SQLite merges all pending handshake data.
  2. Created a **Deep-Probe Handshake Protocol**: Bots now use `MessagesGetDialogs` and `get_chat` on boot to rebuild the cache internally without requiring manual human interaction.
  3. Integrated a **Shared Peer Seeder Listener**: Every bot now listens for pulse messages to dynamically update their caches in the background.

for all Hurdles check: [Survivors Log](Survivors-Log.md)

---------

*Last Updated: 11-02-2026*
*Time: 06:09PM*
