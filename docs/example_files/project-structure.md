Here is the **Master Directory Tree**.

This is exactly how your **VS Code File Sidebar** should look when the Monorepo architecture is fully built. This structure allows "ReadVault" and "StreamVault" to live together without conflicting.

```text
SHADOW-SYSTEMS (Root Project)
├── .github/                        # CI/CD Automation
│   └── workflows/
│       └── deploy.yml              # GitHub Actions (Auto-Deploy to Oracle/HF)
│
├── .gitignore                      # Git rules (Ignores .env, venv, node_modules)
├── .env                            # Local Secrets (Git Ignored)
├── AI_GENERATION_PROMPT.md         # The System Prompt for LLMs
├── docker-compose.yml              # The Master Swarm Orchestration
├── README.md                       # The Project Guide
│
├── apps/                           # MONOREPO APPS
│   │
│   ├── gateway/                    # The Nginx Load Balancer
│   │   ├── Dockerfile
│   │   └── nginx.conf              # Cache Rules & Rate Limiting
│   │
│   ├── manager/                    # The Brain (FastAPI + Manager Bot)
│   │   ├── core/                   # Configs
│   │   │   ├── config.py           # Env Loader
│   │   │   └── security.py         # JWT/Password Logic
│   │   ├── routers/
│   │   │   ├── auth.py             # Magic Link/Guest Auth
│   │   │   ├── admin.py            # Dashboard APIs
│   │   │   ├── library.py          # Search/Filter Movies & Books
│   │   │   └── proxy.py            # Image Obfuscation Route
│   │   ├── services/
│   │   │   ├── bot_manager.py      # Pyrogram Admin Client
│   │   │   ├── database.py         # MongoDB Motor Driver
│   │   │   ├── metadata.py         # TMDB/MAL Scrapers
│   │   │   └── swarm_sync.py       # Redis State Manager
│   │   ├── main.py                 # App Entry Point
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── stream-engine/              # The Muscle (Go Streaming)
│   │   ├── core/
│   │   │   └── downloader.go       # Telegram API Handshake
│   │   ├── utils/
│   │   │   └── ffmpeg_remux.go     # Live Transmuxing Logic
│   │   ├── main.go                 # io.Copy Passthrough Server
│   │   ├── go.mod                  # Go Deps
│   │   └── Dockerfile
│   │
│   ├── web/                        # The Face (Next.js Frontend)
│   │   ├── app/                    # App Router
│   │   │   ├── (auth)/             # Login/Magic Link Routes
│   │   │   ├── admin/              # Admin Console Layouts
│   │   │   ├── read/               # [ReadVault] Reader Layouts
│   │   │   │   └── [manga_id]/...  
│   │   │   ├── watch/              # [StreamVault] Player Layouts
│   │   │   │   └── [movie_id]/...
│   │   │   ├── layout.tsx          # Global Glass Shell
│   │   │   └── page.tsx            # Landing Page
│   │   ├── components/
│   │   │   ├── admin/              # Dashboard Charts/Tables
│   │   │   ├── player/             # Video Player + UI Controls
│   │   │   ├── reader/             # Vertical Scroll/Manga Renderer
│   │   │   └── ui/                 # Shared Glass Atoms (Buttons, Cards)
│   │   ├── lib/
│   │   │   ├── api.ts              # Fetcher for Manager API
│   │   │   └── hooks.ts            # Custom React Hooks
│   │   ├── public/                 # Static Assets
│   │   │   ├── icons/
│   │   │   └── js/
│   │   │       └── ads_core.js     # AdBlock Honeypot
│   │   │   ├── manifest.json       # PWA Configuration (Missing in previous list)
│   │   │   └── sw.js               # PWA Service Worker (Offline Support)
│   │   ├── next.config.mjs
│   │   ├── package.json
│   │   ├── middleware.ts           #  Multi-Tenant Routing Logic (For Franchise Phase)
│   │   └── Dockerfile
│   │
│   ├── worker-manga/               # [ReadVault] Ingestion Worker
│   │   ├── handlers/
│   │   │   └── scraper.py          # Gallery-DL wrapper
│   │   ├── manga_worker.py         # Main Listener
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── worker-video/               # [StreamVault] Heavy Worker
│       ├── handlers/
│       │   ├── leech.py            # Torrent -> Telegram logic
│       │   ├── mirror.py           # PixelDrain/Abyss Uploads
│       │   └── zippery.py          # Zip Pack Creator
│       ├── worker.py               # Main Listener
│       ├── requirements.txt
│       └── Dockerfile
│
├── tools/
│   ├── apkbuilder/                 # here we build PWA Apps for tensnts with (@bubblewrap/cli)
│       └── twa-config.json
├── config/                         # External Configuration Files
│   ├── prometheus.yml              # Monitoring Rules
│   └── workers/                    # Store for Session Strings (Safe Mount)
│       └── .keep
│
├── data/                           # MOUNTED VOLUMES (Data Persistence)
│   ├── cache/                      # 200GB Cache (Mapped to Nginx)
│   ├── mongo/                      # Database Files
│   ├── redis/                      # Redis Memory Dump
│   └── sessions/                   # Bot .session files
│
└── docs/                           # YOUR BLUEPRINT ARCHIVE
    ├── example_files/
    │   ├── Dockerfile.md           # Reference for all Dockerfiles
    │   ├── docker_compose_yml.md   # Reference Wiring
    │   ├── env_example.md          # Secrets Template
    │   ├── nginx_conf.md           # Gateway Logic
    │   └── requirements_txt.md     # Dependency List
    └── v2_blueprint/
        ├── context_01_infrastructure.md
        ├── context_02_telegram_logic.md
        ├── context_03_frontend_ux.md
        ├── context_04_database.md
        ├── context_05_future_roadmap.md
        ├── context_06_admin_panel.md
        ├── context_07_franchise_model.md
        └── context_readvault.md
```

### 🗝️ Key Organizational Rules to Remember

1.  **`/apps` vs `/config`**:
    *   **Apps:** Where your logic (Python/Go/JS Code) lives.
    *   **Config:** Where static settings (Worker sessions, Monitoring rules) live.
2.  **`/data` (The Host Mount):**
    *   When working **Locally (VS Code)**, this folder will grow inside your project.
    *   When working on **Oracle**, this folder maps to the Physical SSD.
    *   **IMPORTANT:** Ensure `.gitignore` includes `data/` and `.env` so you don't accidentally upload your database or keys to GitHub.

This structure allows you to build **ReadVault** (touching only `web` and `worker-manga`) today, and easily add **StreamVault** (touching `stream-engine` and `worker-video`) tomorrow without breaking anything.
