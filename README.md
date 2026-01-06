# 🎬 Shadow Systems: StreamVault + ReadVault (V2)
> **Enterprise-grade streaming backend optimized for Oracle Free Tier (ARM64).**

![Status](https://img.shields.io/badge/Phase-2_Baseline-blue?style=for-the-badge)
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
├── apps/                    # Monorepo Components
│   ├── gateway/             # Nginx Load Balancer (Secure Link Logic)
│   ├── manager/             # FastAPI Brain (Auth, Metadata, API)
│   └── stream-engine/       # Golang High-Performance Passthrough
│   ├── web/                 # Next.js Frontend (Obsidian Glass UI)
│   ├── worker-manga/        # Specialized ReadVault Scrapers
│   ├── worker-video/        # High-Speed Video Swarm
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── worker.py
├── config/                  # External Configuration & Session Storage
├── data/                    # Local Volume Persistence (Cache/Sessions)
├── docs/                    # Architectural Blueprints (Context Files)
├── docker-compose.dev.yml   # "Potato Mode" Development Orchestrator
└── .env.example             # Environmental Secrets
```

---

## 🛠 Operational Status & Achievements

### 🚀 Phase 1: Infrastructure Baseline (COMPLETED)
- **IDX Environment:** Docker daemon bridged via Nix configuration.
- **Internal Networking:** `sv-internal` bridge connecting Nginx and Manager.
- **Persistence Layer:** Successfully established external connection to **MongoDB Atlas** (Metadata) and **Upstash Redis** (State).
- **Worker-Video Swarm:** ONLINE ✅ (Auth DC5 Handshake Verified)

### 🧠 Phase 2: Core Brain (IN PROGRESS)
- **Identity Logic:** @Shadow_systemsBot is fully authenticated via MTProto (DC5).
- **Metadata Ingestion:** Live TMDB integration enabled.
- **Search & Store:** Capable of searching movies and officially indexing them into the cloud database with unique short-slug IDs.
- **Short Link Protection:** Implementation of Base62 unique slug generation for obfuscation.

---

## 🏗 System Protocol (The Golden Rules)
1. **The Gateway Wall:** All media requests MUST proxy through the Nginx Gateway; Raw Telegram URLs are never exposed.
2. **Stateless Workers:** Heavy workers must purge temporary data instantly after the Telegram upload phase.
3. **Multi-Tenancy:** Routes distinguish between different franchise domains based on incoming headers.
4. **Safety Factor:** Swarm rotation limits any single Telegram session to 15 concurrent users to prevent API bans.

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

# Check Nginx Edge Proxy logs
docker logs -f sv-gateway-dev
```

### Halting the Engine
```bash
docker compose -f docker-compose.dev.yml down
```

---

## 📈 Next Step: Stage 3 (Worker & File Linker)
- **Objective:** Deploy `worker-video` to perform the first "Mirroring" test.
- **Mechanism:** Take a Magnet link/Direct link -> Leech into Shadow Storage -> Link back to the Indexed Movie entry in the Database.
- **Achievements Required:** High-speed decryption handshake and concurrent stream distribution.

---

## ✅ Progress Tracker
- [x] Monorepo Folder Skeleton
- [x] Docker Daemon Stabilization
- [x] MongoDB Atlas Bridge
- [x] Manager Bot DC5 Identity Verified
- [x] Library Indexing API (TMDB)
- [x] **Step A: Handshake Baseline** (Worker 1 bot-authorized and idling).
- [ ] **Step B: Transfer Protocol** (Implementing yt-dlp / MediaInfo integration).
- [ ] **Step C: Mirroring Logic** (Linking Telegram Storage IDs back to MongoDB Library).
- [ ] Nginx Secure Link & Slice Caching Validation
- [ ] Frontend Obsidian Glass Shell (Next.js)

---

# 🛠 The Hurdle Log: Challenges & Resolutions
The **"Shadow Survivor's Log"**. It documents every technical roadblock we encountered during Phase 1 & 2 in the Google Project IDX environment and the exact "Shadow Protocol" fixes we applied.

### 1. The Nix "Sudo" Conflict
*   **The Error:** `sudo: /usr/bin/sudo must be owned by uid 0 and have the setuid bit set`.
*   **Description:** Google IDX runs on Nix, which uses an unprivileged environment. Traditional `sudo` commands for permission changes fail because the user doesn't have root-level filesystem modification rights inside the Nix store.
*   **The Fix:** Use the built-in **UID 1000** (standard for IDX) and avoid `sudo` for directory operations. We handled this by adding system service declarations in `.idx/dev.nix`.
*   **Command:** 
    ```bash
    # Instead of sudo, use Nix user identity
    chown -R $(id -u):$(id -g) apps/ config/ data/
    ```

### 2. The Silent Docker Daemon
*   **The Error:** `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`.
*   **Description:** By default, the Docker service isn't "hot" in a new IDX workspace. Even with the package installed, the socket connection isn't bridged.
*   **The Fix:** Explicitly enabled `services.docker.enable = true` in `.idx/dev.nix` and performed an environment **Rebuild**. This creates the persistent socket bridge.
*   **Protocol:** Always "Rebuild Environment" after editing `.idx/dev.nix`.

### 3. The Pymongo/Motor Version Collision
*   **The Error:** `ImportError: cannot import name '_QUERY_OPTIONS' from 'pymongo.cursor'`.
*   **Description:** A breaking change in the `pymongo` driver (v4.7+) removed internal options that the `motor` (async driver) 3.3.2 library relied upon.
*   **The Fix:** Strict version pinning in `requirements.txt`.
*   **Solution:** 
    ```text
    motor==3.3.2
    pymongo==4.6.3 # Locked to prevent internal breakage
    ```

### 4. Atlas Connection "Anonymous" DB Error
*   **The Error:** `pymongo.errors.ConfigurationError: No default database name defined or provided`.
*   **Description:** MongoDB Atlas connection strings often omit the database name at the end of the URL. The standard `get_default_database()` method crashes if the path doesn't end with a `/dbname`.
*   **The Fix:** Patched `database.py` and `worker.py` with a manual fallback check.
*   **Logic:** 
    ```python
    try:
        self.db = mongo_client.get_default_database()
    except Exception:
        self.db = mongo_client["shadow_systems"] # Hardcoded fallback
    ```

### 5. The SQLite "Readonly" Session Error
*   **The Error:** `TELEGRAM CRITICAL: attempt to write a readonly database` (or `unable to open database file`).
*   **Description:** Pyrogram uses SQLite to manage sessions. When mounted inside a Docker container, it needs to create temporary "journal" files. If the parent folder is not globally writable, the OS rejects the creation of the lock file.
*   **The Fix:** Used absolute paths for `workdir` and applied a recursive `777` chmod on the `data/sessions` host folder.
*   **Command:** 
    ```bash
    chmod -R 777 data/sessions
    ```

### 6. Media Parser Library Collision (PTN)
*   **The Error:** `Could not find a version that satisfies the requirement PTN>=2.3.0` and Python 3.10 incompatibility.
*   **Description:** The Torrent Name Parser (`ptn`) library had a naming collision on PyPI with another package. Furthermore, modern versions required Python 3.12, while we were using 3.10.
*   **The Fix:** Upgraded Worker base image to **Python 3.12-slim** and pulled the media parser directly from the official source GitHub repository.
*   **Requirement Solution:** 
    ```text
    git+https://github.com/divijbindlish/parse-torrent-name.git
    ```

### 7. IDX "Welcome to Nginx" 8080 Redirect
*   **The Error:** Seeing the standard Nginx landing page instead of API JSON on the Public URL.
*   **Description:** Browser caching and an over-generalized `location /` block in `nginx.conf` caused the Gateway to serve static files instead of proxying traffic to the Manager Brain.
*   **The Fix:** Refined `nginx.conf` with a specific `/api/` rewrite rule and removed the root landing page, allowing FastAPI to handle root requests directly via the proxy.
*   **Access Pattern:** Use `https://your-url.dev/api/library/list`.

Upon reviewing our detailed interaction logs from the start, there are **three specific hurdles** we encountered that were missing from the previous log. I have generated them here for your `README.md` or `DEBUG_LOG.md`.

---

### 8. The "Root package.json" Preview Crash
*   **The Error:** `Error: ENOENT: no such file or directory, open '/home/user/shadow-systems/package.json'`.
*   **Description:** Google Project IDX’s "Web Preview" logic defaults to looking for a Node.js `package.json` in the root folder to start a development server. Since Shadow Systems is a monorepo and our frontend is inside `apps/web/`, IDX failed to launch.
*   **The Fix:** Updated `.idx/dev.nix` to change the preview command to `tail -f /dev/null`. This satisfies IDX's need for a running command while allowing our **Nginx Gateway (Port 8080)** to handle the actual traffic via Docker.

### 9. Python Package Discovery Failure
*   **The Error:** `ImportError: cannot import name 'bot_manager' from 'services.bot_manager'`.
*   **Description:** Python does not automatically treat folders as "packages" unless they contain an initialization file. This caused the Manager Brain to fail during boot as it couldn't see our custom services.
*   **The Fix:** Manually initialized the package structure.
*   **Command:** 
    ```bash
    touch apps/manager/core/__init__.py apps/manager/services/__init__.py
    ```

### 10. The "DCNone" / Handshake Shutdown Loop
*   **The Error:** `ConnectionError: Client is already terminated` followed by `KeyError: 0`.
*   **Description:** During the first Telegram handshake in a new container, Pyrogram often cycles through different Data Centers (DCs). If the app is shut down while this handshake is happening (due to a restart or an error), it creates a corrupted local SQLite session file.
*   **The Fix:** Wrapped the `bot.stop()` logic in a `try/except` block and added a manual check for `app.is_connected`.
*   **Protocol:** Before restarting a failed bot, always wipe the specific `.session` file in `data/sessions/` to ensure a clean handshake.

---

**Everything from the first `mkdir` to the successful DC5 handshake of the Worker is now accounted for.**

------
*Last Updated: 2026-01-05*
