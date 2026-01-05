### 🧠 Shadow Systems: Operator Commands (Phase 2 Baseline)

---

#### 🏗️ 1. Orchestration (Docker Compose)
*Manage the lifecycle of the entire infrastructure using the development config.*

```bash
# --- START & BUILD ---

# Use On of these To stop Containers
docker compose -f docker-compose.dev.yml down # For all at once
docker stop $(docker ps -a -q) # for all at once
docker stop {ContainerID} # For one by one

# Use this to launch all services or update them after a code change
docker compose -f docker-compose.dev.yml up -d --build


# --- STOP & CLEAN ---
# Stop all containers but keep data (removes the virtual network)
docker compose -f docker-compose.dev.yml down

# --- SERVICE MANAGEMENT ---
# Example 1: Restart only the brain (useful for refreshing metadata logic)
docker compose -f docker-compose.dev.yml restart manager

# Example 2: Update specifically the gateway after changing nginx.conf
docker compose -f docker-compose.dev.yml up -d --build gateway
```

---

#### 🔍 2. Observability (Logs & Health)
*Monitoring the internal heartbeat of the "Shadow Brain."*

```bash
# --- LIVE LOGS ---
# Example 1: Watch the bot and database connections in real-time
docker logs -f sv-manager-dev

# Example 2: Inspect Nginx traffic and request forwarding
docker logs -f sv-gateway-dev

# --- RESOURCE METRICS ---
# Check live container health and memory usage (Critical in Potato Mode)
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Check RAM/CPU usage of all containers (Critical for IDX performance)
docker stats --no-stream

# --- PROCESS VERIFICATION ---
# Verify which ports are active and container names
docker ps
```

---

#### 💻 3. Infrastructure Control (Linux & Shell)
*Direct manipulation of the host environment and container interiors.*

```bash
# --- PERMISSION HARDENING ---
# Example 1: Ensure session files are writable by the bot service
chmod -R 777 data/sessions

# Example 2: Fix workspace ownership after creating new files
chown -R $(id -u):$(id -g) apps/ config/ data/

# --- INTERNAL SHELL ACCESS ---
# Example 1: Enter the Manager's bash for manual Python debugging
docker exec -it sv-manager-dev bash

# Example 2: Verify folder mapping inside the container
docker exec sv-manager-dev ls -R /app/sessions

# --- DISK PURGE (Potato Defense) ---
# Removes old Docker image layers to prevent "No Space Left on Device"
docker system prune -f

# Clean the Nginx Video Cache (Manual override)
docker exec -it sv-gateway-dev sh -c "rm -rf /var/cache/nginx/streamvault/*"
```

---

#### 📡 4. API Interaction (Curl Testing)
*Communicating with the Gateway (Port 8080) to drive logic through the endpoints.*

```bash
# --- SYSTEM HEALTH ---
# Example 1: Basic heartbeat check
curl http://localhost:8080/api/health

# --- CONTENT INGESTION ---
# Example 1: Search live on TMDB (Does not save to DB)
curl "http://localhost:8080/api/library/search?q=Inception"

# Example 2: Save metadata to MongoDB Atlas (Index action)
curl -X POST http://localhost:8080/api/library/index/movie/27205

# --- DATA VERIFICATION ---
# Example 1: Retrieve all movies currently in your Cloud DB
curl http://localhost:8080/api/library/list

# Example 2: View a specific movie details using its Short ID
curl http://localhost:8080/api/library/view/v7K1wP2
```

---

#### 🐙 5. Repository Management (Git Sync)
*Saving progress and version-tagging stable milestones.*

```bash
# --- SNAPSHOT & SYNC ---
# Stage all changes (new routers, configs, logic)
git add .

# Create an immutable version point
git commit -m "feat: content ingestion router and database text indexing"

# --- REMOTE BACKUP ---
# Push logic to the main branch on GitHub
git push origin main

# --- VERSIONING ---
# Example 1: Tag current state as functional core
git tag -a v0.3-core-api -m "Library logic and Bot handshake stable"

# Example 2: Send tags to remote repo for deployment visibility
git push --tags

# --- For code push repo authentication ---
# Format: https://{YOUR_USERNAME}:{YOUR_TOKEN}@github.com/{USERNAME}/{REPO_NAME}.git
git remote set-url origin https://YourUsername:ghp_yourTokenHERE@github.com/DCspare/ShadowSystems-DevMode.git
```
