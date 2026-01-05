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
- [ ] Worker Leech Implementation
- [ ] Nginx Secure Link & Slice Caching Validation
- [ ] Frontend Obsidian Glass Shell (Next.js)

---
*Last Updated: 2026-01-05*
