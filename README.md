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
├── apps/                         # Monorepo Components
│   ├── gateway/                  # Nginx Load Balancer (Secure Link Logic)
│   │   ├── Dockerfile
│   │   └── nginx.conf.template
│   ├── manager/                  # FastAPI Brain (Auth, Metadata, API)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── security.py
│       │   └── utils.py
│       ├── handlers/
│       │   └── cmd_leech.py
│       ├── routers/
│       │   └── library.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── bot_manager.py
│       │   ├── database.py
│       │   └── metadata.py
│       ├── Dockerfile
│       ├── main.py
│       └── requirements.txt
│   ├── shared/                   # 🟢 NEW: Shared Kernel (The "Dry" Logic)
│   │   ├── formatter.py          # Centralized Telegram visual styling
│   │   ├── schemas.py            # Pydantic Sources of Truth
│   │   └── settings.py      
│   ├── stream-engine/            # Golang High-Performance Passthrough
│       ├── core/
│       │   ├── downloader.py
│       │   └── telegram.py
│       ├── Dockerfile
│       └── main.go
│   ├── web/                      # Next.js Frontend (Obsidian Glass UI)
│   ├── worker-manga/             # Specialized ReadVault Scrapers
│   ├── worker-video/             # High-Speed Video Swarm
│       ├── handlers/             # Logic Pipelines
│       │   ├── downloader.py     # Hybrid Aria2 + Native HTTP Engine
│       │   ├── flow_ingest.py    # Identity Sanitization & Transfer Core 
│       │   └── processor.py      # FFmpeg Media & Screenshot Engine
│       ├── Dockerfile            # Python 3.12 Media Image
│       ├── entrypoint.sh
│       ├── requirements.txt      # Version-pinned Media Libs
│       └── worker.py             # Redis Task Watcher & Bot identity
├── config/                       # External Configuration & Session Storage
├── data/                         # Local Volume Persistence (Cache/Sessions)
├── docs/                         # Architectural Blueprints (Context Files)
├── .dockerignore
├── .env.example                  # Environmental Secrets
├── .gitignore
├── docker-compose.dev.yml        # "Potato Mode" Development Orchestrator
├── gen_session.py
├── README.md
└── Survivors-Logs.md
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
- [x] **Smart Series Mapping:** Implemented `PTN` logic with a Fallback RegEx to detect `SxxExx` patterns. Episodes now automatically sort into nested MongoDB Season buckets (`seasons.1`, `seasons.2`).
- [x] **Atomic Transactions:** Secured the Leech pipeline with "Cleanup-Finally" blocks and strict Database Upsert paths (Skeleton Creation vs Enrichment Update) to prevent data corruption.

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
[Survivors-Log.md](Survivors-Log.md)

---------

*Last Updated: 2026-01-17*
*Time: 003:45pm*
