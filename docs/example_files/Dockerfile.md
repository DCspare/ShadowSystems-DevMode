Here is the complete list of **Dockerfiles** required for your **Monorepo Structure** (`/apps/...`).

These files include the critical **Oracle A1 (ARM64)** optimizations, **Permission Fixes (`chown 1000`)**, and necessary binaries (**FFmpeg, Gallery-DL**).

---

### 1. The Brain: Manager API & Bots
**Path:** `apps/manager/Dockerfile`
**Role:** Runs the FastAPI Backend + Manager Bot Logic.

```dockerfile
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# 1. System Dependencies (GCC for compilation, FFmpeg for probing)
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Workdir
WORKDIR /app

# 3. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Code
COPY . .

# 5. PERMISSIONS (Critical for Oracle Host Volumes)
# We ensure the app user (1000) owns the files so it can write to mapped volumes
RUN useradd -m -u 1000 user \
    && chown -R 1000:1000 /app

# 6. Switch User & Run
USER 1000
CMD ["sh", "-c", "python3 main.py"]
```

---

### 2. The Muscle: Video Worker (StreamVault)
**Path:** `apps/worker-video/Dockerfile`
**Role:** Downloads massive video files, zips packets, uploads to Telegram.

```dockerfile
FROM python:3.10-slim

# Env: Forces stdout to flush immediately (Critical for live logs)
ENV PYTHONUNBUFFERED=1

# 1. System Dependencies (FFmpeg for Screens/Subs, 7zip for Packs)
# 'mediainfo': robust metadata fallback
# 'procps': required for some monitoring scripts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    mediainfo \
    aria2 \
    p7zip-full \
    curl \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Workdir
WORKDIR /app

# 3. Install Python Deps (Pyrogram, TgCrypto)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Code
COPY . .

# 5. Fix Permissions Session Files
RUN useradd -m -u 1000 user \
    && chown -R 1000:1000 /app

USER 1000
CMD ["python3", "worker.py"]
```

---

### 3. The Librarian: Manga Worker (ReadVault)
**Path:** `apps/worker-manga/Dockerfile`
**Role:** Scrapes Images using `gallery-dl`. Ideal for Hugging Face or Oracle.

```dockerfile
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# 1. System Deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Workdir
WORKDIR /app

# 3. Install Tools (Gallery-DL) & Python Deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly update gallery-dl to master (Sites break often)
RUN pip install --no-cache-dir -U https://github.com/mikf/gallery-dl/archive/master.tar.gz

# 4. Copy Code
COPY . .

# 5. Temp Storage (Ephemeral for Hugging Face/Docker)
# Ensure the worker can delete temp files
RUN mkdir -p /tmp/downloads && chown -R 1000:1000 /tmp/downloads

USER 1000
CMD ["python3", "manga_worker.py"]
```

---

### 4. The Engine: Go Stream Core (V2 Performance)
**Path:** `apps/stream-engine/Dockerfile`
**Role:** `io.Copy` Passthrough + Live Remuxing (Golang).

```dockerfile
# Stage 1: Build (Compiling Go to Binary)
FROM golang:1.22-alpine AS builder
WORKDIR /app

# Install Git (Required to fetch Go modules)
RUN apk add --no-cache git

COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o stream-engine .

# Stage 2: Runtime (Lightweight Alpine)
FROM alpine:latest

# Install FFmpeg for Live Remuxing (MKV -> MP4)
RUN apk add --no-cache ffmpeg ca-certificates

WORKDIR /app
COPY --from=builder /app/stream-engine .

# Expose Port 8000
EXPOSE 8000

# Permissions
RUN adduser -D -u 1000 user \
    && chown -R 1000:1000 /app

USER 1000
CMD ["./stream-engine"]
```

---

### 5. The Face: Frontend (Next.js)
**Path:** `apps/web/Dockerfile`
**Role:** Runs the Glassmorphism Website (SSR). Optimized for "Standalone" build.

```dockerfile
# Stage 1: Base
FROM node:20-alpine AS base

# Install libc6-compat (Needed for Sharp/Image Optimization on Alpine)
RUN apk add --no-cache libc6-compat

# Stage 2: Deps
FROM base AS deps
WORKDIR /app
COPY package.json yarn.lock* package-lock.json* ./
# Install 'sharp' for Next/Image optimization (Critical for Manga)
RUN npm ci

# Stage 3: Builder
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Disable Next.js Telemetry
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# Stage 4: Runner
FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Permissions
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy Standalone Build (Tiny Size)
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
```

---

### 6. The Gateway: Nginx (Oracle Load Balancer)
**Path:** `apps/gateway/Dockerfile`
**Role:** Caching + SSL Termination + Throttling.

```dockerfile
FROM nginx:alpine

# 1. Install utilities (if needed for debugging)
RUN apk add --no-cache apache2-utils

# 2. Copy Config
COPY nginx.conf /etc/nginx/nginx.conf

# 3. Create Cache Directory
RUN mkdir -p /var/cache/nginx/streamvault \
    && chown -R 101:101 /var/cache/nginx

# 4. Volume Mount Note
# In docker-compose, we will mount the 150GB Host Path here:
# - /var/lib/oracle/streamvault_cache:/var/cache/nginx/streamvault

EXPOSE 80 443
```

---

### 📦 Root `docker-compose.yml` (Wiring it all)
This connects the files above. Save in root.

```yaml
version: "3.8"

services:
  # -------------------------
  # 1. THE GATEWAY (Load Balancer & Cache)
  # -------------------------
  gateway:
    build: ./apps/gateway
    container_name: streamvault-gateway
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      # Mount Oracle Host Volume for Cache
      - ./data/cache:/var/cache/nginx/streamvault
    depends_on:
      - manager
      - web
      - stream-engine
    networks:
      - sv-internal

  # -------------------------
  # 2. THE BRAIN (Manager API)
  # -------------------------
  manager:
    build: ./apps/manager
    container_name: streamvault-manager
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data/sessions:/app/sessions
    depends_on:
      - db-mongo
      - db-redis
    networks:
      - sv-internal

  # -------------------------
  # 3. THE ENGINE (Streaming)
  # -------------------------
  stream-engine:
    build: ./apps/stream-engine
    container_name: streamvault-engine
    restart: unless-stopped
    expose:
      - "8000"
    networks:
      - sv-internal

  # -------------------------
  # 4. THE FACE (Frontend)
  # -------------------------
  web:
    build: ./apps/web
    container_name: streamvault-web
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=http://gateway  # Internal routing via Nginx
    expose:
      - "3000"
    networks:
      - sv-internal

  # -------------------------
  # 5. THE WORKERS (Swarm)
  # -------------------------
  worker-video:
    build: ./apps/worker-video
    container_name: worker-video
    restart: unless-stopped
    env_file: .env
    depends_on:
      - db-mongo
    volumes:
./config/cookies.txt:/app/cookies.txt:ro  # Read Only mount for auth
     networks:
      - sv-internal

  worker-manga:
    build: ./apps/worker-manga
    container_name: worker-manga
    restart: unless-stopped
    env_file: .env
    volumes:
./config/cookies.txt:/app/cookies.txt:ro  # Read Only mount for auth
    networks:
      - sv-internal

  # -------------------------
  # 6. DATA LAYER (Databases)
  # -------------------------
  db-mongo:
    image: mongo:6.0
    container_name: sv-mongo
    restart: always
    volumes:
      - ./data/mongo:/data/db
    networks:
      - sv-internal

  db-redis:
    image: redis:alpine
    container_name: sv-redis
    restart: always
    volumes:
      - ./data/redis:/data
    networks:
      - sv-internal

  # -------------------------
  # 7. OPS LAYER (Monitoring)
  # -------------------------
  # Using a single image bundle for low-resource environments (Optional)
  monitor:
    image: prom/prometheus
    container_name: sv-monitor
    restart: unless-stopped
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
    expose:
      - "9090"
    networks:
      - sv-internal

# -------------------------
# NETWORKS
# -------------------------
networks:
  sv-internal:
    driver: bridge
```
