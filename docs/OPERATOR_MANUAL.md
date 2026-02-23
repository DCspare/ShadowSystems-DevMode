### 🧠 Shadow Systems: Operator Commands (Phase 2 Baseline)

---

#### 🏗️ 1. Orchestration (Docker Compose)
*Manage the lifecycle of the entire infrastructure using the development config.*

```bash
# --- START & BUILD ---

# Use On of these To stop Containers
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

docker compose -f docker-compose.dev.yml build --no-cache worker-video
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

#### 💻 3 A. Infrastructure Control (Linux & Shell)
*Direct manipulation of the host environment and container interiors.*

```bash
# --- PERMISSION HARDENING ---
# Example 1: Ensure session files are writable by the bot service
# Force the session folder to be writable and owned by your current IDX user
chown -R 1000:1000 data/sessions/

chmod -R 777 data/sessions

# Example 2: Fix workspace ownership after creating new files
chown -R $(id -u):$(id -g) apps/ config/ data/

# --- INTERNAL SHELL ACCESS ---
# Example 1: Enter the Manager's bash for manual Python debugging
docker exec -it sv-manager-dev bash

# Example 2: Verify folder mapping inside the container
docker exec sv-manager-dev ls -R /app/sessions

# --- DISK PURGE (Potato Defense) ---
# To check Total RAM + Swap (--mega, --kilo, --giga)
free -t --giga 

# Removes old Docker image layers to prevent "No Space Left on Device"
docker system prune -f

# Clean the Nginx Video Cache (Manual override)
docker exec -it sv-gateway-dev sh -c "rm -rf /var/cache/nginx/streamvault/*"
```

#### 🧹 3 B: The "Aggressive Prune" Script
*Running `docker system prune` is good, but `prune --volumes` is better for dev work (cleans up orphan DB/Cache volumes), and `prune -a` removes unused images (old builds).*


```bash
# 1. Stop everything
docker compose -f docker-compose.dev.yml down

# 2. Nuclear Clean (Removes stopped containers + unused networks + dangling images + build cache)
docker system prune -af --volumes

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

#### 🐙 5 A. Repository Management (Git Sync)
*Saving progress and version-tagging stable milestones.*

```bash
# --- SNAPSHOT & SYNC ---
# Stage all changes (new routers, configs, logic)
git add .

# Create an immutable version point
git commit -m "feat: content ingestion router and database text indexing"

# --- REMOTE BACKUP ---
# Push branch to the remote repo
git push origin main

OR

# git push -u origin feat/shared-downloader
# -u is short form for --set-upstream flag
git switch main
git push -u origin <branch-name>

# --- VERSIONING ---
# Example 1: Tag current state as functional core
git tag -a v0.3-core-api -m "Library logic and Bot handshake stable"

# Example 2: Send tags to remote repo for deployment visibility
git push --tags

# --- For code push repo authentication ---
# Format: https://{YOUR_USERNAME}:{YOUR_TOKEN}@github.com/{USERNAME}/{REPO_NAME}.git
git remote set-url origin https://YourUsername:ghp_yourTokenHERE@github.com/DCspare/ShadowSystems-DevMode.git
```

#### 🕸️ 5 B. Git Feature Workflow (Safety Net)
*Standard procedure for starting new code to avoid breaking `main`.*

```bash
# 1. START: Create a new branch for a feature (e.g., frontend player)
git checkout -b feat/frontend-player

# 2. SAVE: Stage and commit changes frequently
git add .
git commit -m "feat(web): Added ArtPlayer component"

# 3. MERGE: Switch back to main and merge when perfect
git checkout main
git pull origin main
git merge feat/frontend-player

# 4. RELEASE: Tag a stable version
git tag -a v0.4.0 -m "Frontend Alpha"
git push origin main --tags

# 5. CLEANUP: Delete the feature branch
git branch -d feat/frontend-player
```

---

#### 🧪 6. Real World Diagnostics (Shadow Protocols)
*Specific workflows to fix common issues faced during development.*

**Scenario A: The "Stuck Bot" (Fixing Peer/Channel Invalid Errors)**
*Use this when the Worker or Stream Engine fails to upload/stream because it "Forgot" the channel hash.*

```bash
# 1. Watch the Worker Log for "Peer ID Invalid" or "Handshake Failed"
docker logs -f sv-worker-video-dev

# 2. Watch the Stream Engine for "Channel Not Found" or "File Reference Expired"
docker logs -f sv-stream-engine-dev

# 3. THE FIX: Go to your Telegram "ShadowSystems Log" channel and send:
/health

# 4. Verify in Logs:
# You should see: "✅ Found Target Channel" or "📩 Stream Engine received update"
```

**Scenario B: Database Hygiene (Fixing Bad Leech Metadata)**
*Use this when you leeched a file using the wrong TMDB ID, and now your database has a "Skeleton" entry you need to wipe.*

```bash
# 1. Search to find the incorrect TMDB_ID
curl "http://localhost:8080/api/library/search?q=WrongMovie"

# 2. NUKE the entry from MongoDB (Does not delete file from Telegram)
curl -X DELETE http://localhost:8080/api/library/delete/12345

# 3. Manually Index the CORRECT Metadata (Pre-leech)
curl -X POST http://localhost:8080/api/library/index/movie/99999
```

**Scenario C: Identity Generation (The Session String)**
*How to generate the `TG_SESSION_STRING` without running the whole Docker stack.*

```bash
# 1. Install dependencies locally (if Python is installed on host)
pip install pyrogram tgcrypto 
OR 
source .venv/bin/activate # if .venv is available

# 2. Create the generator script (if missing)
cat <<EOF > gen_session.py
import asyncio
from pyrogram import Client
api_id = input("API ID: ")
api_hash = input("API HASH: ")
async def main():
    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        print(await app.export_session_string())
if __name__ == "__main__": asyncio.run(main())
EOF

# 3. Run and Copy String to .env
python3 gen_session.py
```

---

#### 7. To simulate exactly what the Frontend does: **Browse --> Select --> Sign**.

#### 🕵️ Step 1: Find valid IDs
First, we need to grab a `short_id` and a `telegram_id` from your existing library to test with.

Run this command in your terminal:
```bash
curl -s http://localhost:8080/api/library/list
OR
use browser and go to https://Domain/api/library/list
```

**Look at the output.** Find a movie and copy two things:
1.  **`short_id`** (e.g., `abb276a`)
2.  **`file_id`** (It is inside `files: [{ "file_id": "BQAC..." }]`)

---

### 🔐 Step 2: Request the Signed Link
Now manually hit the **Sign** endpoint using the data you just copied.

**Command:**
*(Replace `YOUR_SHORT_ID` and `YOUR_FILE_ID/telegram_id` with the real text you copied above)*

```bash # DEV Mode
curl -X POST http://localhost:8080/api/library/sign \
  -H "Content-Type: application/json" \
  -d '{
    "short_id": "YOUR_SHORT_ID", 
    "file_id": "YOUR_FILE_ID"
  }'
```

#### ✅ Expected Output
You should see a JSON response like this:

```json
{
  "status": "signed",
  "stream_url": "/stream/BQAC...?token=...&expires=...",
  "expires_in": 14400
}
```

If you see `token=` and `expires=`, **Logic is Valid.** You successfully completely separated the data from the secure link.

---

#### 🎬 Step 3: Test the Stream
Take the **`stream_url`** path from the previous output and paste it into this URL in your **IDX Preview Browser** or simply execute:

```bash
curl -I "http://localhost:8080/stream/YOUR_FILE_ID?token=YOUR_TOKEN&expires=YOUR_TIMESTAMP"
```
#### ✅ Expected Output
You should see a JSON response like this:

```json
HTTP/1.1 200 OK
Server: nginx/1.29.4
Date: Fri, 16 Jan 2026 08:42:23 GMT
Content-Type: video/mp4
Content-Length: 43780763
Connection: keep-alive
Accept-Ranges: bytes
Content-Range: bytes 0-43780762/43780763
```

*   **HTTP 200/206:** Success. The key is valid.
*   **HTTP 403 Forbidden:** The IP signing failed (or Nginx didn't like the hash).
    *   *Dev Note:* If you generate the link via **Terminal Curl** but try to play it in **Chrome Browser**, it **might** fail if Nginx detects an IP mismatch (Terminal Container IP vs Browser Tunnel IP). This is a good security feature! To test visual playback, try making the API request directly in the browser address bar for `view`, manually constructing a mock post is hard, so relies on the `curl -I` status code for now.

---

### 🔐 Security Protocols: Admin API Access
*Reference for manual interventions when `MODE=PROD`.*

When the system is in Production Mode, all "Write" operations (`POST`, `PUT`, `DELETE`) and sensitive "Sign" operations are locked behind the Gatekeeper. You must provide the **API Secret** to authorized commands.

**Prerequisite:** Check your `.env` for `API_SECRET_KEY` (e.g., `shadow_super_secret_dev_key`).

#### 1. Generating a Secure Stream Link (Manually)
Used to debug if the Nginx hashing is working for a specific file.

```bash
curl -X POST http://localhost:8080/api/library/sign \
  -H "Content-Type: application/json" \
  -H "X-Shadow-Secret: shadow_super_secret_dev_key" \
  -d '{
    "short_id": "7e2e66a", 
    "file_id": "BQACAgUAAyEGAATEUt8iAAIDIGmDNUJDfclwLMF9RhPzcn5SqeIrAAIlHgACHv4ZVNcpxBopBKULHgQ" 
  }'
```
#### ✅ Expected Output
You should see a JSON response like this:

```json
{"status":"signed","stream_url":"/stream/BQACAgUAAyEGAATEUt8iAAICUWl4fqISaCqr8pOBGwuM_aXDeh6YAAIYIAACbFDBVx5Bhi6nqsCcHgQ?token=IelijU9Xj6uYj0kX2igFBQ&expires=1769867545","expires_in":14400}
```

#### 2. Generating a User ID and Session Token.
```bash
curl -X POST "http://localhost:8080/api/auth/guest" \
  -H "Content-Type: application/json" \
  -H "X-Shadow-Secret: shadow_super_secret_dev_key"
```
#### ✅ Expected Output
You should see a JSON response like this:

```json
{"status":"registered","user_id":"guest_19808686-e32","role":"guest"}
```

--- 

```bash
curl -I -X POST "http://localhost:8080/api/auth/guest" \
  -H "X-Shadow-Secret: shadow_super_secret_dev_key"
```
#### ✅ Expected Output
You should see a JSON response like this:

```json
HTTP/1.1 200 OK
Server: nginx/1.29.4
Date: Sat, 31 Jan 2026 09:45:54 GMT
Content-Type: application/json
Content-Length: 69
Connection: keep-alive
set-cookie: shadow_session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJndWVzdF9kZTdlMjUwMy04YzYiLCJyb2xlIjoiZnJlZSIsImV4cCI6MTc3MDQ1NzU1NH0.eHFhtPPFLiSMe0pWiPhSyC-GtuUvxAxwRVIBSPJpqCQ; HttpOnly; Max-Age=2592000; Path=/; SameSite=lax; Secure
```

#### 2a. Nuking a whole Movie Entry (DELETE)
Used to forcefully remove an entry if the UI is inaccessible.

```bash
curl -X DELETE http://localhost:8080/api/library/delete/106379 \
  -H "X-Shadow-Secret: shadow_super_secret_dev_key"
```
#### 2b. Nuking a whole Movie Entry (remove_file)
*Goal: Remove a file link without deleting the movie meta.*

You need a `tmdb_id` that exists in your database.
1. First, list content to find an ID:
```bash
curl "http://localhost:8080/api/library/list?limit=1"
```
2. Note Down the `tmdb_id` and the `telegram_id` inside the `files` array.
3. Run the deletion:
```bash
# Replace 12345 with real TMDB ID
# Replace ABC_FILE_ID with the telegram file ID from step 1
curl -X DELETE "http://localhost:8080/api/library/remove_file/27205?file_id=BQACAgUAAyEGAATEUt8iAAMmaVzP5IoxCLzligtMG4NT6CJp0yQAAiIgAAJZ8-lWPPRyYh_Bgo8eBA&season=0" \
     -H "X-Shadow-Secret: shadow_super_secret_dev_key"
```

#### ✅ Expected Output
You should see a JSON response like this:

```json
{"status":"removed","tmdb_id":27205,"removed_file":"BQACAgUAAyEGAATEUt8iAANeaV-STmhAr8NXLUncdzQHm7bKLKsAAiIaAAIkSwABV0udxlpUmKfNHgQ"}
```

#### 3. Triggering a Remote Ingest (Leech via API)
Used to automate uploads from external scripts without using Telegram.

```bash
curl -X POST http://localhost:8080/api/attach_file/550?file_path=/path/to/movie.mkv \
  -H "X-Shadow-Secret: shadow_super_secret_dev_key"
```

### 🧪 How to Test On-the-Fly Subtitle Extractor (No Frontend Needed)

1.  **Find a file with subs:**
    Check your library list and find a `file_id` that has a `subtitles` array with an index (e.g., `index: 2`).
    `curl http://localhost:8080/api/library/list`

2.  **Run the Request:**
    Replace `FILE_ID` and `INDEX` with real values from your DB.
    ```bash
    curl -i "http://localhost:8080/api/library/subtitle/FILE_ID/INDEX.vtt"
    ```
e.g. 
```bash
curl -i "http://localhost:8080/api/library/subtitle/BQACAgUAAyEGAATEUt8iAAICfWl4sX7-f3Ikpw-ndui3dnEQwOVoAALAGgACbFDJV5xcngvvRrMWHgQ/3.vtt"
OR 
curl -i "http://localhost:8080/api/library/subtitle/BQACAgUAAyEGAATEUt8iAAICdWl4rV8gjozmM6JvMHjb4TusrF5EAAKxGgACbFDJV-Sy-MW8xQwOHgQ/4.vtt" -o sub.txt # To Save the output in a file
```

3.  **What to look for:**
    *   The `Content-Type` header should be `text/vtt`.
    *   The first line of the output MUST be `WEBVTT`.
    *   Followed by timestamps like `00:00:10.000 --> 00:00:15.000`.
#### ✅ Expected Output
You should see a response like this file:
[Subtitle Output](../sub.txt)


#### To make life easier and get rid of typing long command like `docker compose -f docker-compose.dev.yml` use below command in your local terminal(not in docker container):

`alias dcd='docker compose -f docker-compose.dev.yml'`

Now, you can just type:
dcd up -d
dcd logs -f manager
dcd build

npx repomix --style markdown --include "apps/stream-engine" --output shadow_streamE
ngine.md