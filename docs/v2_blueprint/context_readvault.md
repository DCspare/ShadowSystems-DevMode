> 📂 Phase 2 Blueprint: Project ReadVault (Lite Module)<br>
**Filename:** `docs/v2_blueprint/context_readvault.md`<br>
**Role:** The "Lightweight" Reader Module (Manga, Manhwa, Books, Novels).<br>
**Deploy Target:** Hugging Face Spaces (Backend) + Vercel (Frontend) + MongoDB Atlas.

---

## 🏛️ 1. System Architecture (The Stateless Bridge)
Unlike Video Streaming, ReadVault works on **Short-Burst HTTP Requests**. This allows it to run 100% free on Hugging Face Spaces without crashing, serving as a proxy between Telegram's massive storage and the User.

### The Stack
| Component | Tech | Role |
| :--- | :--- | :--- |
| **Ingestion Worker** | `gallery-dl` + Pyrogram | Runs locally/PC. Bulk-downloads Manga/Manhwa and uploads them to Telegram as **Albums**. |
| **Backend API** | Python (FastAPI) | Hosted on **Hugging Face Space**. Stateless Proxy. Fetches Images/PDFs from Telegram RAM and pipes to Frontend. |
| **Database** | MongoDB Atlas | Free Tier. Stores Library Metadata and User Progress. |
| **Frontend** | Next.js 14 | Hosted on **Vercel/Cloudflare**. Renders the Reader Interface with infinite scroll. |
| **Storage** | Telegram Channels | Infinite Storage. Images stored as Album MediaGroups. |

---

## 💾 2. Data Schema: The Unified Library

### The `books` Collection (Metadata)
```json
{
  "_id": "manga_solo_leveling",    // Unique Slug
  "media_type": "manga",           // manga | comic | novel
  "content_rating": "safe",        // safe | 18+ (Filtered from guest search)
  "title": "Solo Leveling",
  "author": "Chugong",
  "genres": ["Action", "Fantasy", "Manhwa"],
  "status": "ended",               // Used for UI Tags
  "cover_image": "AgADxxxx",       // Telegram File ID (Poster)
  
  // 📖 READER DATA (The Index)
  "chapters": [
    {
      "chap": 1.0,
      "title": "I'm Used to It",
      "pages_count": 45,
      "storage_id": "-100xxxx",     // Channel ID
      
      // Payload: List of Telegram IDs for the pages
      "pages": [ "file_id_p1", "file_id_p2", "file_id_p3" ... ]
    },
    { "chap": 1.5, ... }           // Decimal support for ".5" chapters
  ],
  "files": [                       // For PDF/EPUB downloads
    { "format": "PDF", "file_id": "doc_id_x", "size": "14MB" }
  ]
}
```

### The `users` Collection (Bookmarks Upgrade)
*Merged into the main StreamVault User object.*
```json
"read_history": {
  "manga_solo_leveling": {
    "last_chapter": 55.0,
    "last_page_index": 12,
    "last_read_at": ISODate("...")
  }
}
```

---

## 🤖 3. The Bots: Ingestion & Management

### The Manager Bot (ReadVault Admin)
*   **Role:** Metadata scraping, User Search, and Abuse control.
*   **Batch Ingest:** Command `/batch [URL]` triggers the Worker to scrape entire series from sites like MangaDex.
*   **"Peek" Search:** Users can search `@Bot Name`. Bot returns a "Peek Card" with the cover and a button to **Read Chapter 1** instantly on the web.
*   **CDN Cache Purger**
  Command `/purge_cache [Manga_ID]` that calls the Cloudflare/Vercel API to invalidate cache tags (e.g., `tag:manga-solo-leveling`) across the edge network.
  *Essential for instantly fixing "Wrong Page" errors without waiting for the 1-year cache to expire.*

### The Worker Bot (The Librarian)
*   **Workflow (Visuals):**
    1.  Downloads Chapter X Images to RAM via `gallery-dl`.
    2.  Uploads as **MediaGroup** to the dedicated `Manga_Log_Channel`.
    3.  Passes File IDs to Manager for indexing.
*   **Workflow (Docs):**
    1.  Downloads PDF/EPUB.
    2.  Uses `pikepdf` to inject "StreamVault" branding into metadata.
    3.  Uploads to `Book_Log_Channel`.

---

## 🎨 4. Frontend Experience (Next.js Reader)

### Interface Logic
*   **Unified Search:** Toggle "Watch (Video)" vs "Read (Manga)".
*   **Manga Page:**
    *   **Hero Section:** Glass-style metadata (Author, Rating).
    *   **Preview Mode:** Hovering the cover fades in "Page 1" behind the text.
    *   **Chapter Grid:** Visual blocks for chapters. "Read" badge if found in User History.

### The Reader Component
*   **Modes:**
    *   **Vertical (Webtoon):** Images stitched seamlessly (`gap-0`) with Lazy Loading.
    *   **Paged (Classic):** Single page Click-to-Next (Left or Right direction).
*   **Progress Sync:**
    *   React `IntersectionObserver` detects which image is on screen.
    *   Updates `localStorage` instantly.
    *   Syncs to DB (via API) every 30 seconds or on "Exit".
*   **Navigation:**
    *   **Sticky Header:** Shows "Ch 1 > Page 5".
    *   **Chapter Switcher:** Dropdown to jump chapters without going back to menu.

### Frontend Survival
- [ ] **Cloudflare Pages Host:**
  *   Deploy specifically to CF Pages (not Vercel) for better DMCA resilience.
  *   **CORS Fix:** Ensure Backend (`main.py`) `CORSMiddleware` explicitly allows `https://*.pages.dev`.

---

## 🔒 5. Backend Logic (FastAPI on HF Space)

### The "Blind Relay" (Image Proxy)
*   **Route:** `GET /api/proxy/image/{telegram_file_id}?group_id={manga_id}`
*   **Mechanism:** 
    1. Fetches bytes from Telegram RAM.
    2. Sets Headers for aggressive Caching:
       * `Cache-Control: public, max-age=31536000, immutable` (Browser Cache 1 Year).
       * `CDN-Cache-Control: max-age=31536000` (Edge Cache 1 Year).
       * `Cache-Tag: manga-{manga_id}` (Groups all pages of one manga for bulk purging).
    3. Pipes binary stream to Browser.
*   **Anonymity:** Hides Telegram origin. To the internet, this looks like a static asset served from your domain.

### The CBZ Downloader (Offline Reading)
*   **Route:** `GET /api/download/cbz/{manga_id}/{chap}`
*   **Mechanism:**
    1.  User clicks "Download Chapter".
    2.  Backend pulls all 50 images of that chapter from Telegram.
    3.  Backend creates a Zip stream in RAM.
    4.  Browser receives `Title_Ch1.cbz` (Comic Book Archive).
    *   *Ad Gate:* Downloading requires passing a Link Shortener (Revenue).

### 18+ Shield & Anonymity
*   **Search Filter:** `18+` content hidden by default. Unlocked via "Login" or "Cookie Toggle".
*   **Hugging Face Defense:** Since HF strictly bans NSFW hosting, our backend is a **Transient Proxy**. It never *saves* the files to the container disk, it just streams the bytes. This avoids Terms of Service detection algorithms which usually scan the file system.

---

## 💰 6. Monetization Strategy

### The "Inter-Chapter" Ad
*   **Trigger:** When user finishes Chapter X and clicks "Next Chapter".
*   **Action:**
    1.  Show Full-Screen Interstitial Ad (Pop-up or Modal).
    2.  Wait 3 seconds.
    3.  Load Chapter X+1.
*   *Why:* Manga reading is fast. Placing ads *between* chapters ensures high viewability without breaking immersion *during* the read.

---

## 📄 7. Deployment Checklist (Lite Phase)

- [ ] **1. Telegram:** Create `Manga_Storage_Channel` and `Book_Storage_Channel`.
- [ ] **2. Hugging Face:** Deploy Docker-based FastAPI Backend (Worker + Manager).
- [ ] **3. Vercel:** Deploy Next.js Frontend with Environment Variables connecting to HF API.
- [ ] **4. Database:** Set up MongoDB Atlas "Library" and "User" collections.
- [ ] **5. Ingest:** Run local script to mass-upload Top 50 Manhwa (Foundation Library).
