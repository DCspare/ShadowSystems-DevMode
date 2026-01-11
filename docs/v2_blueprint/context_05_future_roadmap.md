 📂 Phase 3 Blueprint: Future Roadmap & Expansions
> **Filename:** `docs/v2_blueprint/context_05_future_roadmap.md`<br>
**Role:** Specification for "Day 2" features that expand ecosystem accessibility beyond the browser (External Apps, TV Automation, RSS).<br>
**Prerequisites:** Requires V2 (Oracle) or Lite (ReadVault) to be operational.

---

## 📚 1. OPDS Standard Support (ReadVault Expansion)
**Objective:** Allow users to read Manga/Books using native applications (Mihon, Tachiyomi, Moon+ Reader) instead of the browser.

### A. Architecture
The Backend (FastAPI) acts as an **OPDS Feed Server**. It translates MongoDB metadata into the **Atom XML** standard required by e-reader apps.

*   **Compatibility Target:** Mihon (Android), Paperback (iOS), Moon+ Reader.
*   **Security:** Uses "URL Token Authentication" (`/opds/{user_api_key}/catalog`) since generic readers struggle with custom Cookie logic.

### B. Endpoints Strategy
- [ ] **The Root Catalog**
  *   `GET /opds/{token}/catalog`
  *   Returns the top-level categories: "Latest Updates", "Popular Manga", "All Books", "Search".
- [ ] **Feed Generation (XML)**
  *   Logic to convert a MongoDB Book Entity into an Atom Entry `<entry>`.
  *   Must populate `<link type="image/jpeg" rel="http://opds-spec.org/image" href="...">` pointing to the ReadVault **Image Proxy**.
- [ ] **Search Bridge**
  *   `GET /opds/{token}/search?q={query}`
  *   Maps the Reader App's search bar query directly to the MongoDB Text Index.
- [ ] **Manifest & Pagination**
  *   Implementation of "Next Page" links in XML to support browsing libraries with 10,000+ titles.

### C. Chapter Serving
Unlike web browsers, OPDS readers need specific navigation for "Page 1 -> Page 2".
- [ ] **Page Streaming Logic:** The `<link rel="http://opds-spec.org/acquisition" ...>` must point to a dedicated zip stream or a standard **Image Manifest** endpoint that lists all page URLs in order.

---

## 🧩 2. Stremio Addon Server (StreamVault Expansion)
**Objective:** Allow users to watch movies/series on Smart TVs (Android TV/Firestick) via the popular Stremio app interface.

### A. The "Manifest"
- [ ] **Route:** `GET /stremio/manifest.json`
- [ ] **Role:** Advertises the "StreamVault" addon to the Stremio ecosystem.
- [ ] **Structure:** Defines which content types we provide (`movie`, `series`) and which catalogs we populate.

### B. Catalog & Meta Handling
- [ ] **Catalog Service:** `GET /stremio/catalog/{type}/{id}.json`
- [ ] **Meta Service:** Maps MongoDB data to the "Cinemeta" standard used by Stremio. Critical for making the "Episodes" tab appear correctly for TV Series.

### C. Stream Resolving (The Money Shot)
- [ ] **Stream Service:** `GET /stremio/stream/{type}/{id}.json`
- [ ] **Logic:**
    1.  User clicks "Play" on TV.
    2.  Stremio requests stream for `tmdb:12345`.
    3.  Manager Bot checks Database.
    4.  **Response:** Returns a JSON Object containing the **Direct Stream URL** (`streamvault.net/stream/{file_id}`).
    *   *Ad Integration Note:* Stremio makes injecting ads harder. This is a "Premium Only" feature.

---

## 🤖 3. Automated "Sonarr" Intelligence (RSS)
**Objective:** Remove the need for manual Leech commands. The bot "Self-Feeds" new content.

### A. The RSS Watcher
- [ ] **Feed Source:** Admin adds "Target Feeds" (e.g., Nyaa.si (Anime), MagnetDL (Movies), ShowRSS (Series)) to MongoDB.
- [ ] **Filter Logic:** Regex based filters (e.g., `/(One Piece|Demon Slayer).+1080p/i`).
- [ ] **Frequency:** Manager Bot checks feed every 15 minutes.

### B. The Auto-Grabber
- [ ] **Dupe Check:** Checks MongoDB to ensure we haven't already indexed this episode.
- [ ] **Ingestion Trigger:** Automatically dispatches the Magnet Link to a "Free" Worker in the swarm.
- [ ] **Notification:** Auto-posts "New Episode Landed" card to the Public Update Channel once processing is complete.

---

## 🗳️ 4. The Request Hub (Ombi Style)
**Objective:** A social "Upvote" system for filling content gaps.

### A. Frontend Interface
- [ ] **Discover Page:** "Popular/Trending" rail showing content *missing* from our DB (sourced via TMDB Discover API).
- [ ] **Action:** "Request This" button.

### B. Backend Logic
- [ ] **Request Queue:** MongoDB Collection `requests` tracks user demand.
- [ ] **Voting:** If User B requests a movie User A already asked for, `votes` count increments to 2.
- [ ] **Threshold Automation:** If `votes > 10`, automatically promote the Request to the **RSS Watcher** or **Leech Queue** to find it.

---

## 🗃️ 5. Collections & Reading Lists
**Objective:** Curated bundling of content for "Binge" consumption.

### A. Data Relation
- [ ] **Tagging System:** DB Support for a `collections` array (e.g., `["marvel_phase_1", "halloween_special"]`).
- [ ] **Admin Tools:** Simple UI to select 50 movies and assign them a Collection Tag.

### B. UI Experience
- [ ] **Carousel Row:** Dedicated Home Page rows for active collections ("Featured: The MCU Saga").
- [ ] **Smart Playlist:** When a user plays Movie 1 in a collection, the "Up Next" button automatically routes to Movie 2.

---

## 🎧 6. Audio Engine Expansion (Audiobooks & Light Novels)
**Objective:** Increase "Time-on-Site" by supporting passive listening formats (`.mp3`, `.m4b`) for commuters and visual novel fans.

*   **Ingestion (Worker Swarm):**
    - [ ] **Audio Downloader Module:** Logic in Worker to process Audiobook sources (LibriVox, YouTube playlists) and upload them as `audio` or `voice` messages to Telegram to preserve metadata/cover art.
*   **Frontend (The Player):**
    - [ ] **Sticky Audio Player:** specialized UI that persists at the bottom of the screen while navigating.
    - [ ] **Speed Controls:** "Podcast Style" playback rate toggles (1.0x, 1.5x, 2.0x, 3.0x).
*   **Database Schema:**
    - [ ] New `media_type: "audiobook"` supporting `chapters` (list of mp3 files) and `duration` fields.

## 🤖 7. 3rd-Party Tracking Sync (AniList / MAL)
**Objective:** Retain power users by auto-syncing their watch/read progress to external tracking sites (The "Hardcore" audience requirement).

*   **Authentication:**
    - [ ] **OAuth2 Bridge:** Logic in Manager API to handle `Login with AniList` flows, storing the User's External Access Token securely in MongoDB (`users` collection).
*   **Progress Hooks:**
    - [ ] **Video Watcher:** Trigger API call to `graphql.anilist.co` when video reaches 90% completion.
    - [ ] **Manga Reader:** Trigger API call when the last page of a chapter is rendered on screen.
    - [ ] **Background Sync:** A low-priority task queue that pushes updates so it doesn't lag the frontend.

## 📉 8. "Data Saver" Middleware (Optimization)
**Objective:** Improve performance for mobile users on weak connections (4G) by reducing image sizes by 80%.

*   **The Processor:**
    - [ ] **On-the-Fly Conversion:** Update the Image Proxy (`/api/proxy/image/{id}`) to check for a `?quality=saver` parameter.
    - [ ] **Compression Logic:** If `saver=true`, Backend reads the Telegram Image $\to$ uses `Pillow` library to convert to **WebP (Q=75)** $\to$ Pipes smaller result to browser.
*   **User Interface:**
    - [ ] **Global Toggle:** A "Lightning Mode" switch in the Sidebar/Settings.
    - [ ] **Cookie Persistence:** Remembers preference across sessions to serve compressed assets automatically.

## 🍿 9. ShadowParty (Sync-Watch System)
**Objective:** Create "Virtual Living Rooms" where multiple users can watch a movie in perfect sync, increasing platform retention.

### A. Architecture
*   **Transport:** WebSockets (`ws://`) managed by FastAPI.
*   **State:** Ephemeral State stored in **Redis**. (No permanent DB records needed for rooms).
    *   Key: `room:88219:status` -> `{ "video_id": "tmdb_123", "timestamp": 120.5, "is_paused": false }`

### B. Logic Flow
1.  **Room Creation:** User clicks "Start Party" -> Backend generates 6-digit Code -> Frontend redirects to Party UI.
2.  **Sync Mechanism:**
    *   **Host Event:** Host pauses/seeks -> Sends Signal -> Backend Publishes to Redis Channel -> Broadcasts to all peers.
    *   **Rubber Banding:** Every 5 seconds, clients report timestamps. If a client drifts >3 seconds from Host, the Frontend auto-seeks to catch up.
3.  **Ghost Chat:** An overlay ephemeral chat sidebar. History is cleared immediately when the room closes (Privacy First).

### C. UX Implementation
*   **Share Link:** `https://shadow.xyz/watch/party/{room_code}` (Deep links directly to the player).
*   **Admin Override:** Admin console capability to send "Global System Alerts" to all active socket connections (e.g., "Server Restarting").

## 🧠 10. Content Enrichment & Schedule Engine
**Objective:** Transform the site from a "Folder" into a "Wiki", and automate the release calendar.

### A. The Metadata Deep-Dive
*   **Source:** Expand TMDB/Jikan scrapers to fetch `/credits` (Cast/Crew) and `/images` (High-res Backdrops).
*   **Database Storage Strategy:**
    *   Store `cast` as an array of objects: `[{ "tmdb_id": 123, "name": "Actor", "role": "Main", "img": "url" }]`.
    *   **Performance:** Create a Multikey Index on `cast.tmdb_id`. This allows instant "Cross-Linking" (Finding all movies where Actor ID 123 appears) without creating a massive new relational table.
*   **Display:** "Cast Grid" on Details Page. Hovering shows character Name.

### B. Simulcast Scheduler Logic
*   **The Backend Job:** Cron job scans "Ongoing" Series/Anime in DB via AniList/TVMaze API.
*   **Action:** Updates a `next_airing` (ISO Date) field in the `series` collection.
*   **Frontend Output:** A dedicated JSON endpoint `/api/schedule/weekly` populates the "VoidAnime-Style" Weekly Calendar.

## 🚀 11. Stream Engine V3 (The `gotd` Upgrade)
**Objective:** Reduce streaming RAM usage from ~15MB (Python/Pyrogram) to ~150KB (Golang).

### A. Architecture Shift
*   **Library:** Replace standard HTTP/Python libraries with **`gotd/td`** (Native MTProto implementation for Golang).
*   **Logic:**
    *   Eliminates the Python->C wrapper overhead.
    *   Establishes raw **TCP sockets** directly to Telegram Datacenters within the Go binary.
    *   **Pipe:** `Telegram TCP Socket` -> `IO Pipe` -> `User HTTP Response`.
*   **Benefit:** Allows the Oracle Free Tier to handle approx **3x - 5x more concurrent users** per CPU core compared to Phase 2.

## 💎 12. "Debrid" Hybrid Caching
**Objective:** Eliminate Telegram Leech waiting times for viral content by tapping into cached torrent clouds.

### A. Integration
*   **Provider:** Real-Debrid / AllDebrid API integration (Admin Account).
*   **Workflow (The "Instant" Check):**
    1.  User requests popular torrent/movie.
    2.  System checks Debrid API hash cache.
    3.  **Yes:** System generates a specialized "Unrestricted Link" and streams DIRECTLY from Debrid (10Gbps line) to the User. *Zero Telegram usage.*
    4.  **No:** System falls back to standard Worker Swarm (Telegram Leech).
    
---

**End of Phase 3 Blueprint.**
This file represents the long-term scaling path once the Phase 2 (Oracle) system is stable.
