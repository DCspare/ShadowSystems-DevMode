📂 Phase 2 Blueprint: Growth, Retention & Survival Ops<br>
> **Filename:** `docs/v2_blueprint/context_09_growth_survival.md`<br>
**Role:** Defining the specialized subsystems for Traffic Retention, SEO Metadata enhancement, File Operations, and Anti-Ban protocols.

---

## 🔔 1. The Retention Engine (Web Push)
**Goal:** Convert "Drive-by" traffic into returning users using OneSignal Web Push.

### A. Infrastructure (Service Worker Merge)
Since Next.js runs a PWA `sw.js`, we must merge OneSignal's worker to prevent conflicts.
*   **Location:** `apps/web/public/sw.js`
*   **Logic:**
    ```javascript
    importScripts('https://cdn.onesignal.com/sdks/web/v16/OneSignalSDKWorker.js');
    // ... PWA Workbox logic follows ...
    ```
*   **Frontend Init:**
    *   Initialize OneSignal with `allowLocalhostAsSecureOrigin: true` (for dev).
    *   Explicitly set `serviceWorkerPath: 'sw.js'` in config to force using the merged file.

### B. Trigger Strategy ("Don't Spam")
*   **Ghost Library Hook:** When user requests a "Missing" movie (`status: missing`), show button **"Notify Me When Available"**. Tags user with `waiting_for: tmdb_ID`.
*   **Manga Update Hook:** At the end of a Chapter, show **"Subscribe to Series"**. Tags user with `manga: manga_ID`.

### C. Automation (The Trigger)
*   **Manager Bot Logic:**
    *   On `ingestion_complete` event -> Query MongoDB for `users.tags`.
    *   IF release matches tag -> Call OneSignal REST API.
    *   **Payload:** "Avatar 3 is now Streaming in 4K!" -> Deep Link to `/watch/avatar-3`.

---

## 🎬 2. SEO Enhancement (Auto-Trailers)
**Goal:** Increase "Time on Page" and Click-Through Rate (CTR) via Google Video Schema.

### A. Scraper Logic
*   **Source:** TMDB API `/movie/{id}/videos`.
*   **Filter:** `type="Trailer"` AND `site="YouTube"`.
*   **Storage:** Save the `youtube_key` inside the `visuals` object of the Movie Schema. Applicable to both **Active** and **Ghost** entries.

### B. Frontend Implementation (Privacy & Performance)
*   **Technique:** Facade Pattern. Load a static JPG first. Load Iframe on click.
*   **Privacy Parameters (The Leech Block):**
    *   Append `?autoplay=1&mute=1&modestbranding=1&rel=0&iv_load_policy=3`.
    *   *Effect:* Hides YouTube logo, prevents "Related Videos" from stealing traffic, hides annotations.
*   **Ghost Page UI:**
    *   Play the trailer **Muted & Looped** in the background "Hero" section (under glass layer) to create immersion and reduce bounce rate.

---

## 📂 3. Ops: ShadowExplorer (Visual TeleDrive)
**Goal:** Visual management of Telegram files without using the Telegram App. Hosted inside the Admin Panel.

### A. Interface
*   **View:** Grid/List of files mapped to the `TG_LOG_CHANNEL`.
*   **Live Preview:** Proxy route `/api/stream/preview/{file_id}` streams the first 10MB to verify Audio/Language.
*   **Visual Status:**
    *   🟢 **Linked:** Exists in Channel & MongoDB.
    *   🟡 **Orphan:** Exists in Channel ONLY (Wasted space).
    *   🔴 **Broken:** Exists in DB, missing in Channel.

### B. Functions
*   **Orphan Purge:** Button to compare DB vs Channel List -> Delete unlinked files from Telegram to free up slot limits.
*   **Thumbnail Fixer:** Context menu to "Upload Cover".
    *   *Action:* Leech Worker downloads video header -> Injects new Cover JPG -> Re-uploads file -> Updates DB reference -> Deletes ugly file.
*   **Limits:** Browser Upload (Drag-n-Drop) restricted to **50MB** (Posters, Subs). Heavy video uploads must use "URL Leech" or "Local Tunnel" command line.

---

## 🔥 4. Security: The Bot Warmer (Incubator)
**Goal:** Preventing "Instant Ban" on fresh Worker Accounts by simulating human behavior history.

### A. The "Trust Score" Protocol
*   **Logic:** A specific script (`warmer.py`) runs in the worker container when `status: warming`.
*   **Duration:** 48 Hours minimum.

### B. The 3 Phases
1.  **Newborn (0-24h):**
    *   Join specific Safe Channels (NASA, Bloomberg, Telegram Tips).
    *   Scroll history (random delays). **NO Downloads.**
2.  **Adolescent (24-48h):**
    *   Send randomized Reactions (👍, ❤️) to posts.
    *   Set Profile Picture (Abstract/AI Face).
    *   Enable 2FA.
3.  **Graduate (48h+):**
    *   Flag set to `active`. Allowed to join Private Log Channels and begin slow leeching.

### C. The "Entropy" Algorithm
*   **Anti-Pattern:** Never run actions on :00 seconds or fixed intervals.
*   **Randomness:** `await asyncio.sleep(random.randint(600, 3200))` between actions.
*   **Target List:** Pulls from `config/warmer_targets.txt` to vary channel choices per bot.

## 📡 5. Satellite Configuration (Unkillable Connectivity)
**Goal:** Decouple the App connection logic from the main domain to survive bans without losing users.

### A. The "Satellite Array" Logic
*   **Frontend Logic:** On startup (`lib/api.ts`), the app attempts to fetch `config.json` from a redundancy list:
    1.  `raw.githubusercontent.com/.../status.json` (Primary)
    2.  `gitlab.com/.../status.json` (Backup)
*   **The Artifact:** JSON file containing `{"active_node": "https://api.new-domain.xyz"}`.
*   **Healing:** If the fetched node URL differs from `localStorage`, the App updates the base URL for all future API calls instantly.

## 📜 6. Matrix View (Centralized Log Streamer)
**Goal:** Debugging Swarm workers without SSH/Terminal access via the Admin Panel.

### A. Architecture
*   **Source:** Manager container mounts host socket: `/var/run/docker.sock:/var/run/docker.sock:ro`.
*   **Backend:** FastAPI route (`ws://api/logs/{container_id}`) streams logs line-by-line using the `docker` Python SDK.
*   **Frontend:** Terminal-like UI rendering the stream live with regex color coding (Red for "Error/Flood").

### B. Requirements
*   **Library:** Manager `requirements.txt` must include `docker==7.0.0`.
*   **Permissions:** Host must run `chmod 666 /var/run/docker.sock` so the container user (1000) can read it.

## 🕵️ 7. The DMCA Defense (Honey-Pot Strategy)
**Goal:** Divert automated legal threats into a slow queue while protecting Domain Authority.

### A. The Page (`/dmca`)
*   **Honey-Pot Text:** Standard legalese promising a response, directing bots to a Form rather than an email link (stops scraper spam).
*   **SEO Masking:** Layout MUST export `metadata = { robots: { index: false } }` to prevent Google from associating "Piracy Legal Issues" with your search ranking.

### B. The Backend Hook
*   **Form:** Integrated with **Cloudflare Turnstile** (Strict).
*   **Storage:** Submissions route to the MongoDB `reports` collection with `type: 'legal'`.
*   **Workflow:** These tickets appear in the Admin Panel "Medic Center" with High Priority (Red Badge).
---

### 8: Catastrophic Protocol.
## 1. The "Nuclear Option" (Remote Data Wipe)
**Goal:** Protection against physical server seizure or deep audits.

### A. The "Destroy" Logic
*   **Trigger:** Special Admin Command `/destroy_evidence [SECRET_KEY]`.
*   **Backend Action:**
    1.  **Container Kill:** Stops all Docker containers immediately.
    2.  **Shredding:** Executes `shred -u -z -n 3` on the `/data/mongo`, `/data/sessions`, and `.env` paths (overwrites data with random noise 3 times before deletion).
    3.  **Logs:** Wipes local syslogs.
    *   **Result:** The VPS remains accessible, but contains 0% evidence of piracy operation.
