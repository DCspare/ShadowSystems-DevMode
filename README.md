# 🎬 Shadow Systems: StreamVault + ReadVault (V2)

> **Role:** Distributed Monorepo for Cinema & Manga Automation.
> **Current Environment:** Google Project IDX (Potato-Mode Dev Swarm).

---

## 🏗️ Monorepo Architecture
The system is divided into functional domains within the `apps/` directory.

- **gateway**: Nginx Edge Proxy (Secure links & Slice Caching).
- **manager**: FastAPI Backend (The Brain + Bot Identity).
- **stream-engine**: Go Binary (The Muscle for Video Passthrough).
- **web**: Next.js 14 Frontend (Obsidian Glass UI).
- **worker-video**: Heavy Lifter for Media Ingestion.
- **worker-manga**: Specialized Scraper for Gallery-DL.

---

## 🚀 Quick Start (Development)

1. **Environment Initialization:**
   Ensure your `.env` is populated with MongoDB Atlas, Upstash Redis, and Telegram API keys.

2. **Start the Micro-Swarm:**
   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   ```

3. **Check Connection Health:**
   ```bash
   docker logs sv-manager-dev
   ```

---

## ✅ Progress Tracker (Phase 2-DEV)
- [x] **Step 1: Environment Baseline** (Google IDX + Docker Provisioning).
- [x] **Step 2: External Persistance** (Atlas + Upstash Handshake verified).
- [x] **Step 3: Identity** (@Shadow_systemsBot is Live on MTProto DC5).
- [ ] **Step 4: Content Management** (Library Router & Scrapers).
- [ ] **Step 5: Frontend Layout** (Next.js Bento Grid initialization).

---

## 📜 System Protocol
- **No Direct Telegram URLs:** Everything is proxied via the Gateway.
- **Stateless Ingestion:** Workers clean up /tmp after every upload.
- **Secure Link Integrity:** Nginx verifies SHA256 hashes for all streaming requests.

