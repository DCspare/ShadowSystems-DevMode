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
├── apps/                               # Core application services
│   ├── gateway/                        # NGINX Reverse Proxy and Entrypoint
│   │   ├── Dockerfile                  # Builds the NGINX image
│   │   └── nginx.conf.template         # NGINX configuration template with ENV support
│   ├── manager/                        # FastAPI Backend (Admin Panel, API, & Bot Logic)
│   │   ├── core/                       # Fundamental app configuration and security
│   │   │   ├── __init__.py             # Python package marker
│   │   │   ├── config.md               # [DEPRECATED] (Now managed via Pydantic settings)
│   │   │   ├── security.py             # JWT, Auth, and Security middleware
│   │   │   └── utils.md                # [DEPRECATED] (Replaced by shared/utils.py)
│   │   ├── handlers/                   # Telegram bot command handlers
│   │   │   ├── __init__.py             # Python package marker
│   │   │   └── cmd_leech.py            # Logic for handling /leech commands
│   │   ├── routers/                    # API route definitions (FastAPI)
│   │   │   ├── admin.py                # Dashboard and system management APIs
│   │   │   ├── auth.py                 # Magic Link and Session Auth APIs
│   │   │   └── library.py              # Media library search and management APIs
│   │   ├── services/                   # Business logic and external integrations
│   │   │   ├── __init__.py             # Python package marker
│   │   │   ├── bot_manager.py          # Pyrogram Admin Client Management
│   │   │   ├── database.md             # [DEPRECATED] (Now handled by apps/shared/database.py)
│   │   │   └── metadata.py             # TMDB/MAL Scrapers for movie/anime info
│   │   ├── Dockerfile                  # Containerizes the FastAPI manager
│   │   ├── main.py                     # FastAPI application entry point
│   │   ├── requirements.txt            # Python dependencies for the manager service
│   ├── shared/                         # Common logic shared across all Python services
│   │   ├── ext_utils/                  # Extended utility functions
│   │   │   ├── exceptions.py           # Custom exception definitions
│   │   │   ├── help_messages.py        # Static strings for Telegram help commands
│   │   │   ├── links_utils.py          # URL parsing and link validation logic
│   │   │   └── status_utils.py         # Formatting utilities for task status messages
│   │   ├── status_utils/               # Specific status formatters for engines
│   │   │   ├── aria2_status.py         # Aria2 task status generator
│   │   │   └── yt_dlp_status.py        # yt-dlp task status generator
│   │   ├── __init__.py                 # Python package marker
│   │   ├── database.py                 # Centralized MongoDB connection logic
│   │   ├── formatter.py                # Visual styling for Telegram messages
│   │   ├── progress.py                 # Logic for calculating speed and ETA
│   │   ├── registry.py                 # Shared state/task tracker
│   │   ├── schemas.py                  # Pydantic models (Data Sources of Truth)
│   │   ├── settings.py                 # Master configuration (Environment variables)
│   │   ├── tg_client.py                # Reusable Telegram client wrapper
│   │   └── utils.py                    # Generic shared utility functions
│   ├── stream-engine/                  # Golang High-Performance Data Passthrough
│   │   ├── core/                       # Internal Go logic
│   │   │   ├── downloader.go           # Logic for chunking and streaming from TG
│   │   │   └── telegram.go             # Telegram API connection management
│   │   ├── Dockerfile                  # Builds the Go stream-engine binary
│   │   ├── go.mod                      # Go dependency management
│   │   ├── go.sum                      # Go dependency checksums
│   │   └── main.go                     # Entry point for the Go stream server
│   ├── web/                            # Next.js Frontend (Obsidian Glass UI) [Placeholder]
│   │   ├── app/                        # Next.js App Router structure
│   │   ├── components/                 # Reusable React UI components
│   │   │   ├── admin/                  # Admin-specific components
│   │   │   ├── player/                 # Video/Audio player components
│   │   │   ├── reader/                 # Manga/Book reader components
│   │   │   └── ui/                     # Basic UI primitives
│   │   ├── lib/                        # Frontend library functions
│   │   └── public/                     # Static assets
│   │       └── js/                     # Client-side JavaScript
│   │           └── ads_core.js         # Core logic for ad delivery (placeholder)
│   ├── worker-manga/                   # Specialized worker for manga processing
│   │   └── handlers/                   # Manga-specific task handlers
│   └── worker-video/                   # High-performance video processing worker
│       ├── downloads/                  # Temporary storage for active downloads
│       ├── handlers/                   # Task-specific logic
│       │   ├── listeners/              # Protocol-specific listeners
│       │   │   └── task_listener.py    # Logic for listening to task queues
│       │   ├── mirror_leech_utils/     # Ported legacy utilities
│       │   │   ├── download_utils/     # Legacy download helper functions
│       │   │   │   ├── __init__.py     # Python package marker
│       │   │   │   ├── aria2_download.py     # Legacy Aria2 helper
│       │   │   │   ├── direct_link_generator_license.md # License for direct link scripts
│       │   │   │   ├── direct_link_generator.py    # Logic for parsing direct download links
│       │   │   │   └── yt_dlp_download.py    # Legacy yt-dlp helper
│       │   │   ├── __init__.py         # Python package marker
│       │   ├── download_manager.py     # Orchestrates download lifecycle
│       │   ├── downloader.md           # [DEPRECATED] (Functionality moved to engines/)
│       │   ├── flow_ingest.py          # Main worker task pipeline (DL -> Process -> Upload)
│       │   ├── processor.py            # Video processing (FFmpeg, thumbnails, metadata)
│       │   └── status_manager.py       # Telegram status update orchestration
│       ├── cookies.txt                 # Scraper auth cookies
│       ├── Dockerfile                  # Builds the video worker image
│       ├── entrypoint.sh               # Environment setup and startup script
│       ├── requirements.txt            # Python dependencies for video worker
│       └── worker.py                   # Celery/Task Worker entry point
├── config/                             # Global system configuration
│   └── workers/                        # Worker-specific configurations
│       └── prometheus.yml              # Prometheus metrics configuration
├── data/                               # Persistent data volumes (ignored by git)
│   ├── cache/                          # Redis/Temporary cache storage
│   ├── mongo/                          # MongoDB database files
│   ├── redis/                          # Redis database files
│   └── sessions/                       # Active Telegram session storage
├── docs/                               # System documentation
│   ├── example_files/                  # Template files for deployment and config
│   │   ├── Dockerfile.md               # Reference documentation for Docker builds
│   │   ├── env_example.md              # Template for environment variables
│   │   ├── gitignore.md                # Template for .gitignore patterns
│   │   ├── nginx_conf.md               # Reference for NGINX routing
│   │   ├── project-structure.md        # Reference project architecture
│   │   ├── prometheus_yml.md           # Reference for monitoring setup
│   │   └── requirements_txt.md         # Reference for python dependencies
│   └── v2_blueprint/                   # Architectural planning and AI contexts
│   │   ├── AI_DeveloperMode_PROMPT.md  # System prompt for development AI
│   │   ├── AI_ReadVault_PROMPT.md      # AI instructions for manga subsystem
│   │   ├── AI_StreamVault_PROMPT.md    # AI instructions for video subsystem
│   │   ├── context_01_infrastructure.md    # Infrastructure and deployment specs
│   │   ├── context_02_frontend_ux.md       # Design and UX guidelines
│   │   ├── context_03_telegram_logic.md    # Bot behavior and logic specs
│   │   ├── context_04_database.md          # Schema and data flow specs
│   │   ├── context_05_future_roadmap.md    # Planned features and scale targets
│   │   ├── context_06_admin_panel.md       # Manager dashboard requirements
│   │   ├── context_07_franchise_model.md   # Multi-instance scaling logic
│   │   ├── context_08_monetization_ads.md  # Revenue and ad strategy
│   │   ├── context_09_growth_survival.md   # Product growth and retention plans
│   │   ├── context_10_development_workflow.md # Git and CI/CD procedures
│   │   ├── context_11_music_engine.md      # Audio streaming subsystem specs
│   │   ├── context_readvault.md            # Manga engine core logic specs
│   │   ├── Extra_Bot_Features.md           # Wishlist of secondary features
│   │   ├── GIT_WORKFLOW.md                 # Git branch and commit standards
│   │   └── README.md                       # Blueprint introduction
│   ├── OPERATOR_MANUAL.md              # Instruction manual for system administrators
├── Ideas/                              # Research, inspiration, and analysis
│   ├── mirror-leech-telegram-bot/      # Analysis of source project 1
│   ├── TG-FileStreamBot/               # Analysis of source project 2
│   ├── WZML-X/                         # Analysis of source project 3
│   └── File Tree.md                    # Detailed project structure overview (Our Workspace)
├── .dockerignore                       # Exclusions for Docker builds
├── .env.example                        # Template for required environment variables
├── .gitignore                          # Exclusions for Git version control
├── docker-compose.dev.yml              # Local orchestration for development
├── gen_session.py                      # Utility to generate Pyrogram sessions
├── pyproject.toml                      # Modern Python project configuration [Ruff]
├── README.md                           # Main project overview and quickstart
├── sub.txt                             # Sample subtitle for testing
└── Survivors-Log.md                    # Technical log of issues and resolutions
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

### 💎 Achievements (v0.8.0-delta) - Industrial Concurrency
- [x] **Path Isolation Protocol**: Implemented unique task sandboxes (`/app/downloads/{task_id}`) allowing 100% safe parallel processing without filename collisions.
- [x] **Metadata Orchestrator**: Decoupled API logic into a dedicated `MetadataService`. Integrated Jikan (MAL) `/full` and `/characters` endpoints for deep-dive anime enrichment.
- [x] **Anime Intelligence**: Added tracking for Voice Actors, Characters, and high-res episode stills. Implemented trailer extraction via Regex for entries missing native YouTube IDs.
- [x] **Strict Routing Logic**: Developed a "Circuit Breaker" within the episode mapper to prevent Movie IDs (TMDB) from being incorrectly indexed as Series based on filename noise.
- [x] **Fault-Tolerant Notifications**: Built a "Peer Fallback" system. Bot now routes error logs to the Admin Channel if the user's Peer ID is unreachable, ensuring zero silent failures.
- [x] **Atomic Persistence**: Fixed MongoDB "Double-Indexing" by utilizing direct `_id` reference passing during the upload-to-index transition.


### Downloading and Uploading Refactored:
Key Changes:
- Registry: Migrated task_dict from raw dictionaries to polymorphic Status Objects.
- Status Utils: Implemented Aria2Status and YtDlpStatus for engine-specific math 
  (speed, ETA, and progress) providing 100% UI stability.
- Task Listener: Introduced TaskListener as the central lifecycle orchestrator 
  handling Download -> Rename -> Process -> Upload transitions.
- Engines: Modularized Aria2 and YT-DLP into mirror_leech_utils, enabling 
  isolated execution and robust error handling.
- Direct Link Generator: Integrated WZML-X bypass logic for high-speed direct 
  downloads from 50+ file hosts (Mediafire, Gofile, etc.).
- UI/UX: Fixed 'Heartbeat CRASH' in Status Manager; restored terminal progress 
  bars via non-blocking logging hooks in the TaskListener.
- Bug Fixes: Resolved task ID mismatches (8-char vs 10-char hex), 'None.mp4' 
  renaming errors, and Pydantic settings validation for cookie paths.
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

*Last Updated: 23-02-2026*
*Time: 12:09PM*
