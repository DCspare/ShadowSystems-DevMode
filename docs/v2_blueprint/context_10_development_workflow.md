# 📂 Phase 5 Blueprint: "Potato-Mode" Development Workflow
> **Filename:** `docs/v2_blueprint/context_10_development_workflow.md`
**Role:** Configuring a High-Performance Development Environment (Codespaces) to build the project without owning a high-end PC.
**Constraint:** Your laptop cannot handle Docker Desktop or heavy compilation.

---

## ⚠️ The Golden Rule
**DO NOT use `docker-compose.yml` (Root) for development.**
It attempts to spin up 10 Workers, Grafana, and Nginx. This will crash GitHub Codespaces (or your laptop).

**ALWAYS** use `docker-compose.codespace.yml` which enables "Slim Mode" (1 Worker, Cloud DBs, No Logs).

## 🔑 Step 0: Identity Setup (Session Partitioning)
To test true concurrency (Simultaneous downloading of 4K Movies and Manga Chapters), use distinct phone numbers.

1.  **Main Personal Number:** Used strictly for the **Manager Admin** (interacting with the bot).
2.  **Secondary Number B:** Generate session as `worker_video_1.session`. Used for heavy files.
3.  **Secondary Number C:** Generate session as `worker_manga_1.session`. Used for gallery scraping.
4.  **Action:** Place both `.session` files in `config/workers/` before starting Docker.

---

## ☁️ 1. Persistence Layer (Externalize Data)
Codespaces are ephemeral (they delete themselves after inactivity). If you run databases inside them, you lose your data.

### Step A: External Databases (Free Tiers)
1.  **MongoDB:** Sign up for **MongoDB Atlas** (Free M0 Sandbox).
    *   Get URI: `mongodb+srv://admin:pass@cluster.mongodb.net/shadow_dev`
2.  **Redis:** Sign up for **Upstash Redis** (Free).
    *   Get URI: `rediss://default:pass@endpoint.upstash.io`

### Step B: The Development `.env`
Create `.env` inside your Codespace root:
```env
MODE=DEV
MONGO_URL=your_atlas_url
REDIS_URL=your_upstash_url
# Leave Domain empty for now, auto-filled by Codespaces usually
```

### Step C: Database Initialization (First Run)
Your fresh Cloud Database is missing required Indexes (Text Search will fail).
1.  **Action:** In Codespace Terminal:
    ```bash
    docker compose -f docker-compose.codespace.yml exec manager python3
    ```
2.  **Run this Python Snippet:**
    ```python
    from services.database import db
    import asyncio
    
    async def init():
        print("Creating Indexes...")
        # Unified Search
        await db.library.create_index([("title", "text"), ("author", "text")])
        # User Lookups
        await db.users.create_index("referral.code")
        # Franchise Logic
        await db.library.create_index("short_id", unique=True)
        print("Done!")

    asyncio.run(init())
    ```

---

## 🛠️ 2.A: The "Slim" Orchestration Config
Create a new file in root: **`docker-compose.dev.yml`**.

```yaml
version: "3.8"

services:
  # 1. GATEWAY (Nginx - Testing Caching & Security)
  gateway:
    build: ./apps/gateway
# SAFETY: Wipe cache folder on every start to prevent Codespace Disk Full crash
    command: /bin/sh -c "rm -rf /var/cache/nginx/streamvault/* && nginx -g 'daemon off;'"
    ports: ["80:80"] 
    volumes:
      - ./data/cache:/var/cache/nginx/streamvault
    depends_on:
      - manager
      - web
    networks:
      - sv-internal

  # 2. MANAGER (The Brain + Logs) Phone Number A
  manager:
    build: ./apps/manager
    environment:
      - MODE=DEV
    env_file: .env
    volumes:
      - ./apps/manager:/app 
      - ./data/sessions:/app/sessions
      - /var/run/docker.sock:/var/run/docker.sock # For Matrix View
    depends_on:
      - db-mongo
      - db-redis
      - monitor # Need this to show stats in Admin
    networks:
      - sv-internal

  # 3. MONITORING (Prometheus - Testing Admin Dashboard)
  monitor:
    image: prom/prometheus
    container_name: dev-monitor
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - sv-internal

  # 4. FRONTEND
  web:
    build: ./apps/web
    environment:
      - NODE_ENV=development
    volumes:
        - ./apps/web:/app
    command: npm run dev
    networks:
      - sv-internal

  # 5. STREAM ENGINE
  stream-engine:
    build: ./apps/stream-engine
    networks:
      - sv-internal

  # 6. 🎥 VIDEO WORKER (Heavy Lifter)
  # Assigned Identity: Phone Number B
  worker-video:
    build: ./apps/worker-video
    environment:
      - WORKER_ID=video_1
      - SESSION_FILE=worker_video_1 # Looks for config/workers/worker_video_1.session
    volumes:
        - ./config/workers:/app/sessions # Mount whole folder
        - ./config/cookies.txt:/app/cookies.txt:ro
    env_file: .env
    networks:
      - sv-internal

  # 📖 MANGA WORKER (Librarian)
  # Assigned Identity: Phone Number C
  worker-manga:
    build: ./apps/worker-manga
    environment:
      - WORKER_ID=manga_1
      - SESSION_FILE=worker_manga_1 # Looks for config/workers/worker_manga_1.session
    volumes:
        - ./config/workers:/app/sessions
        - ./config/cookies.txt:/app/cookies.txt:ro
    env_file: .env
    networks:
      - sv-internal

  # CLOUD DBs are configured in .env, so we skip local Mongo/Redis containers here
  # to save some RAM, unless you want them local too.

networks:
  sv-internal:
    driver: bridge

```
*Note: We remove Nginx here because Codespaces/Tunnel handles the port forwarding.*

## 🔒 Step 2.B: Safe Worker Mode (Bot Tokens)
For testing queues and logic without risking Real SIM Cards:
1.  Create a dummy bot via @BotFather.
2.  Add this bot as **Admin** to your Test Log Channel.
3.  **Config:** Set `WORKER_MODE=BOT` in your `.env`.
4.  **Input:** Put the Bot Token in `config/workers/worker_video_1.token` (instead of session file).
*   **Limitation:** Leeching from *other* Telegram channels will fail. Test with URL/Magnets only.

---

## 📡 3. Networking & Franchise Testing (Tunneling)

To test "ShadowStream" vs "AnimeHub" (Multi-tenant Franchise mode), we need two different URLs pointing to the same server.

### The Setup (Inside Codespace Terminal)
1.  **Install Cloudflared:**
    `curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb`
2.  **Start Tunnel 1 (Admin/Global):**
    ```bash
    cloudflared tunnel --url http://localhost:3000 --logfile tunnel1.log &
    # This URL acts as shadow.xyz
    ```
3.  **Start Tunnel 2 (Tenant):**
    ```bash
    cloudflared tunnel --url http://localhost:3000 --logfile tunnel2.log &
    # This URL acts as anime-hub.com
    ```
4.  **Simulate:**
    *   Visit URL 1 -> App sees "Default" -> Shows Main Site.
    *   Visit URL 2 -> Register this domain in MongoDB (`tenants`) -> App sees "Tenant Match" -> Shows Franchise UI.

---

## 🛡️ 4. Code adjustments for Codespaces (CORS)

Codespaces uses dynamic URLs (`https://frightened-turtle-80.app.github.dev`) which confuse security rules.

### Manager `main.py` Update
```python
# Detect if running in Dev Mode
if os.getenv("MODE") == "DEV":
    allow_origins = ["*"] # Allow all dynamic URLs
else:
    allow_origins = ["https://shadow.xyz"]
```

### Next.js `next.config.mjs`
To avoid "Invalid Host" errors when tunnelled:
```javascript
// Add allowed hostnames for images
images: {
    remotePatterns: [{ hostname: '*.trycloudflare.com' }]
}
```

### Next.js Dev Proxy (Simulating Nginx)
Since we don't run Nginx in Codespaces, we must configure Next.js to route `/api` requests to the Backend Container internally.

**Update `apps/web/next.config.mjs`:**
```javascript
const nextConfig = {
  // ... other config ...
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://manager:8000/api/:path*', // Proxy to Docker Container
      },
    ]
  },
};
```
---

## ⏰ 5. The "Time-Out" Contingency (Hours Limit)
If you exhaust your 60 Hours of GitHub Codespaces:

### Plan B: Google Project IDX
1.  Navigate to `idx.google.com`.
2.  Import GitHub Repo.
3.  Add the extensions `Python` and `Docker` from their marketplace.
4.  Run the same commands.

### Plan C: Bare Metal (Low RAM Strategy)
*For running locally on Windows without Docker.*
1.  **Manager:** `cd apps/manager && pip install -r requirements.txt && uvicorn main:app --reload`
2.  **Web:** `cd apps/web && npm install && npm run dev`
3.  **Workers:** Run purely as python scripts (`python worker.py`).
*Note: This bypasses Nginx Secure Links, so you are testing logic, not security.*

## 🎭 6. Simulation Modes (Safety Configs)

### A. Ad/Payment Mocking
To prevent GPlinks/Adsterra bans for "Invalid Traffic" during testing:
1.  **Env Variable:** `MOCK_EXTERNAL_APIS=true`
2.  **Manager Logic:**
    *   Intercepts calls to Shortener APIs. Returns a local URL: `http://localhost:3000/mock-success`.
    *   **Billing Time-Warp:** If enabled, the "Sheriff" Cron Job runs every minute instead of daily, and treats 1 minute as 1 day (to test Franchise expiry logic fast).

### B. Content Seeding ("Big Buck Bunny" Protocol)
Use `scripts/seed_db.py` to populate the UI without illegal downloading.
*   **Action:** Injects 20 "Public Domain" movies (Open-source blender movies) with valid video URLs.
*   **Benefit:** Allows testing the Video Player, Transcoding, and HLS features legally without triggering ISP warnings or consuming excessive disk space.

### C. Database Isolation (Anti-Pollution)
*   **Critical:** Development `MONGO_URL` must point to a specific DB name: `.../shadow_dev?retryWrites=true...`
*   **Why:** Prevents "Test Data" (Fake movies/users) from mixing with eventual "Production Data" since we use the same MongoDB Atlas cluster for both.

---

**Completion:** Use this file as your manual when you open VS Code for the first time. It contains all the bypasses needed to work without a professional server.
