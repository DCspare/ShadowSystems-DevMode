📂 Phase 2 Blueprint: Web Frontend & UX<br>
> **Filename:** `docs/v2_blueprint/context_02_frontend_ux.md`<br>
**Role:** The Visual Layer (Next.js Website) hosted on Oracle (Docker).

---

## 🎨 1. Design System (Identity)

### Visual Style: "Obsidian Glass"
- [ ] **Color Palette**
  Deep Midnight Void (`#050505`) background. Text is off-white (`#ececec`). Accents use Cyberpunk Neon (Cyan/Pink) for high-contrast Call-to-Actions (CTAs).
- [ ] **Glassmorphism Logic (Desktop)**
  Heavily blurred translucent layers (`backdrop-filter: blur(24px)`) for Navbars, Sidebars, and Modals with 1px semi-transparent borders.
- [ ] **Mobile Performance Mode**
  CSS logic (`@media (max-width: 768px)`) that forces solid colors instead of heavy blurs on mobile devices to maintain 60FPS scrolling.
- [ ] **Progressive Web App (PWA)**
  Full `manifest.json` and `service-worker` configuration allowing users to "Install" StreamVault as a native app on Android/iOS.
  *Removes browser address bar (standalone mode) and caches the UI shell for offline access.*
- [ ] **Motion Engine**
  **Framer Motion** handles layout transitions (Bento Grids expanding) and Page Transitions (Fade/Slide) to feel like a Native App.

### Page Structure
- [ ] **The "Hub" (Homepage)**
  Featured "Hero" Banner (Parallax), "Continue Watching" Rail (Local Storage), and Trending "Bento Grid" (Mixed aspect ratio cards).
- [ ] **Catalog & Search**
  Debounced "Instant Search" dropdown (glass overlay). Advanced filters (Genre, Quality, Audio Lang) with infinite scrolling.
- [ ] **Movie/Series Page**
  Full-width Backdrop Glow. Metadata Pills (Rating, Year). **Quality Preview Gallery** (FFmpeg Screenshots) carousel to prove video quality.
- [ ] **The Player**
  Distraction-free "Cinema Mode". Overlay controls for Audio/Subtitle switching.
- [ ] **User Dashboard**
  - **History Tab:** Synced Watch Progress.
  - **Wishlist Tab:** Status of requested movies.
  - **Referral Widget:** "Invite 3 friends to unlock 4K" progress bar + unique invite link copy button.

*   **Feature:** **Resolution Badges.**
*   **Logic:** The UI should scan the `files` array in MongoDB. If it finds both `1080p` and `720p`, it should display little "HD" and "SD" tags on the movie poster.
*   **UX:** This tells the user before they click: "We have this in high quality."

---

## 🏗️ 2. Functional Logic (The Engine)

### A. Authentication: "Public First" Model
- [ ] **Guest Mode (Default)**
  Auto-generates a `guest_id` via Cookie. Allowed to stream (capped at 720p speed). History saved to Browser LocalStorage.
- [ ] **Turnstile Gate**
  **Cloudflare Turnstile** widget integrated into the "Play" button for Guests to verify "Humanity" and stop scraping bots.
- [ ] **Account Linking (Magic Link)**
  - **Auth Logic:** User enters a code or scans QR to bind their Guest Session to a permanent ID via the Backend API.
  - **Magic Link Handler:** Page routes for `/auth/callback?token=...` that exchange the Bot-Generated JWT for a permanent Secure HttpOnly cookie.
  - **Privacy:** Pure token exchange. No Telegram widgets, no phone number sharing on the UI.

### B. Streaming & Downloads
- [ ] **The "Bucket" Modal**
  Download/Play button opens a Modal listing all DB versions (4K, 1080p, 720p). Shows file size and codec details.
- [ ] **Zip-Stream Trigger**
  "Download Season Pack" button logic. Checks size -> If >5GB, triggers Shortener flow -> Opens backend Zip Engine stream.
- [ ] **Adaptive Player (Plyr/ArtPlayer)**
  Configured for HTTP 206 Scrubbing. Dynamic injection of `<track>` tags for Soft Subtitles (`/api/subs/...`).
- [ ] **Failover Logic**
  Javascript event listener on `<video error>`: if Primary Stream (Telegram) fails, auto-swaps `src` to the Backup Mirror (Abyss.to).

- [ ] **Access Protocol Modal (The Choice)**
  *   **UI:** Glass Card overlay on the Player.
  *   **Option 1:** "Watch Free" (VidHide + Ads).
  *   **Option 2:** "Activate Shadow Pass" (Oracle + No Ads + 12h Timer).
  *   **Visuals:** Use the "Lock Icon" and "Timer Icon" to visually communicate the trade-off.

### C 1. The Web Player (Headless Hybrid Engine)
**Core Tech:** **ArtPlayer.js** (Wrapped in React).
*Why:* Provides a robust HLS/VAST engine but allows full "Skinning" to match the Obsidian Glass aesthetic.

- [ ] **Custom Skinning (The "Glass" Overrides):**
    *   **Controls:** Disable default bottom bar. Inject custom transparent controls with CSS `backdrop-filter: blur(20px)`.
    *   **Theme:** Force primary color `#00d8ff` (Neon Cyan) for progress bars/toggles.
    *   **Icons:** Replace default SVGs with `lucide-react` icons for a premium feel.
*   **Internal Settings Menu (Fullscreen Logic):**
    *   **Problem:** External buttons are inaccessible in Fullscreen mode.
    *   **Fix:** Programmatically inject arrays into `art.setting`:
        1.  **Quality:** Switch between 1080p/720p/480p (Reloads `url` property).
        2.  **Source:** Switch between "Shadow VIP" and "Cloud Mirrors".
    *   **Playback Speed:** Add standard 0.5x - 2.0x selector.

- [ ] **The "Layers" API Strategy (Feature Injection):**
    *   Do NOT build overlays outside the video div (avoids fullscreen z-index bugs).
    *   **Use `art.layers.add()` to inject:**
        1.  **Skip Intro Button:** Positioned bottom-right (Time-gated).
        2.  **Status Pills:** "Buffering..." / "Optimizing..." notifications (Top-right).
        3.  **Watermark:** Subtle "Shadow Systems" logo in top-left.

- [ ] **Standard Features (Enabled):**
    *   **Mobile:** Double-tap seek, Long-press 2x speed, Swipe Volume/Brightness.
    *   **Subtitles:** Native VTT support with offset synchronization.
    *   **Picture-in-Picture (PiP):** Auto-enabled for background watching.

- [ ] **Monetization Hooks:**
    *   **VAST Plugin:** `artplayer-plugin-vast` configured for Adsterra Pre-roll.
    *   **Error Fallback:** If VAST error occurs, ArtPlayer `error` event triggers the Pop-under script immediately.
      
### C 2. The Web Player (HTML5)
- [ ] **3-Step Playback Defense**
  Automated error handling logic in the player:
  1.  **Direct Play:** Attempts passthrough streaming (Lowest Latency).
  2.  **Auto-Remux:** If `MediaError` detected (e.g., MKV format), auto-reloads stream with `?mode=remux`.
  3.  **External Intent (VLC):** If codecs fail (e.g., x265 on old device), displays a **"Play in VLC"** button triggering the native URI scheme (`vlc://...` or `intent://...`).
  4. **Transparent Status Messages (UX)**
  *   **Scenario:** Player is waiting for VAST Ad or buffering the main file.
    
- [ ] **UI:** A small, semi-transparent "Glass Pill" notification in the top-right corner of the player.
  *   **States:**
      *   *Connecting:* "🔄 Establishing Secure Connection..." (During VAST load).
      *   *Ad Playing:* "⚡ Buffering 4K Stream in background..." (Psychology: "This ad is helping me").
      *   *Remuxing:* "🛠️ Optimizing Video Format..." (If auto-remux triggers).
  *   **Goal:** Reduces rage-clicks by telling the user exactly what is happening.
*   **Z-Index Rule:** The Status Pill must have `z-index: 9999` (Higher than ArtPlayer/Adsterra Ad Layers) so it floats *over* the advertisement.
    
- [ ] **Multi-Server Selector**
  UI toggle above player to switch between "Shadow-CDN" (Oracle), "Mirror-A" (Abyss), and "Mirror-B" (StreamWish).

- [ ] **Tiered Server Selector:**
  *   **Server 1: Shadow VIP ⚡** (Oracle/Telegram)
      *   *Status:* **LOCKED 🔒** for Guests.
      *   *Action:* Clicking triggers "Login / Premium" modal.
      *   *Features:* 4K, No Ads, Instant Seek.
  *   **Server 2: Cloud ☁️** (VidHide/Embeds)
      *   *Status:* **Default** for Guests.
      *   *Features:* Standard Quality, 3rd-Party Ads.
  *   **Logic:** Smart auto-selects Server 2 if `user.is_premium == false`.
  
- [ ] **VAST/IMA Ad Integration**
  Support for Video-Ads (Pre-roll) via Adsterra VAST tags, integrated directly into the ArtPlayer/Plyr instance.

- [ ] **Server Disclaimer UI**
  *   **Logic:** When a user switches to a "Mirror" server (Abyss/StreamWish):
  *   **Action:** Display a small "Toast" or text badge: "⚠️ You are using a Backup Server. Forced 3rd-party ads may appear. Switch to 'Primary' for an ad-free experience."
  *   **Goal:** Protects your brand reputation by explaining that those annoying ads are not yours.

- [ ] **Slug-Based Routing:**
  *   **Path:** Supports `/v/{short_id}` (e.g., `shadow.xyz/v/v7K1wP2`).
  *   **Obfuscation:** Hides the TMDB ID and original file title from the URL bar to prevent easy scraper indexing.
    
- [ ] **Adaptive VAST Ad Engine:**
  *   **Logic:** Player detects if the current domain is a **Franchise Domain**.
  *   **Action:** If `vast_tag` exists in the tenant config, the player initializes the IMA (Interactive Media Ads) SDK and plays a Video Pre-roll *before* the movie begins.

- [ ] **Community "Skip Intro" Button**
  *   **UI:** An overlay button ("Skip Intro ->") appears during timestamps defined in DB (`intro_start` to `intro_end`).
  *   **Sourcing:** Premium Users can "Vote/Submit" timestamps in the player interface to crowd-source this data.
    
### D. Series & Ongoing Content
- [ ] **Status Indicators**
  Visual tags on posters: "🟢 New Episode" (Ongoing) or "🔴 Complete" (Ended).

- [ ] **Season Tabs**
  AJAX-loaded episode lists separated by Season Tabs to handle long-running shows (e.g., One Piece) without DOM lag.

### E. Cost & DMCA Defense
- [ ] **Static Export Build**
  *   **Config:** `output: 'export'` in `next.config.mjs`.
  *   **Why:** Creates an invincible HTML build deployable on Cloudflare Pages, Netlify, or Nginx anywhere. Decouples site from server.
    
- [ ] **Image Optimization Override (ReadVault Fix)**
  *   **Config:** `images: { unoptimized: true }`.
  *   **Logic:** Force usage of standard `<img>` tags pointing to `API_URL/proxy/image` to bypass Vercel billing limits.
  *   **CLS Prevention:** All manga images must be wrapped in `animate-pulse` skeleton `div`s with Aspect Ratio preservation to stop layout shifts.

- [ ] **PWA Lifecycle Manager (Updater Toast)**
  *   **Event Listener:** Listen for service worker state changes (`waiting` state).
  *   **UI:** Show a "Glass Toast" with a [REFRESH] button when a new build is detected in the background.
  *   **Logic:** `workbox.messageSkipWaiting()` to force the new cache to take over immediately upon click.

---

## 🔒 3. Obfuscation & Security

### A. Privacy Layer
- [ ] **White-Label Image Proxy**
  Renders all TMDB/Telegram images via `/api/image/{id}` route. Browser sees *StreamVault* URL, not *Telescope* URL.

- [ ] **Header Stripping**
  Removes `Server: Next.js` and other identifying headers.

### B. User Safety & Error States
- [ ] **"Broken Link" Modal**
  Context-aware report button. Options: "Wrong Audio", "Buffering", "Dead Link". Submits to Admin Bot.

- [ ] **DMCA Compliance Page**
  Formal "Safe Harbor" text page with a web form for rights holders.

- [ ] **Maintenance Mode (503)**
  A dedicated static "Glass" splash screen that activates if the API is unreachable (during Docker Restarts), preventing ugly browser error pages.

- [ ] **"The Red Pill" (Smart Anti-Inspector)**
  *   **Dev Bypass:** Checks `localStorage.getItem('SHADOW_DEV_BYPASS')`. Use `/?dev_secret=ADMIN_SECRET` to enable this mode.
  *   **Defense (If Bypass False):**
      1.  **Infinite Debugger:** `setInterval(() => { debugger }, 2000)` pauses execution if DevTools opens.
      2.  **UI Shield:** Block Context Menu (Right Click) and F12/Ctrl+Shift+I.
      3.  **Log Cleanse:** Override `console.log` to prevent credential leakage.
    
---

## 💰 4. Monetization Strategy

### A. The Ad Stack
- [ ] **Ad-Block "Soft Wall"**
  Detects ad-script failure. Displays non-intrusive Glass Toast: "Please allow ads to help us pay server costs."

- [ ] **Smart Pop-Unders**
  Injects 1 Pop-under script click listener on the first "Interaction" (Play/Download) per session.

- [ ] **Shortener Gateway (Ad-Link)**
  Logic applied to "Heavy Downloads". Modal: "Verify to Unlock" -> Redirects to Shortener -> Callback sets 1-hour cookie.
---

## 💬 5. Community & Social (Ghost System)

### A. Discussion UI
- [ ] **Ghost Comment Widget**
  A custom, privacy-first comment section that replaces Disqus/Telegram widgets.
  *   **Guest Posting:** Allowed (assigns random "Shadow" ID + Avatar).
  *   **Spoiler Masking:** UI logic to blur text tagged as `>! spoiler !<`.
    
- [ ] **"Hype" Timeline Comments (Danmu)**
  *Feature for Video Player:* Displays user comments as fading text at specific timestamps (e.g., at 10:45) over the video.
  *   **UX:** Creating a communal "Live Watching" feel without requiring a livestream. Toggled via "Show Comments" button.

### B. Anti-Abuse (Frontend)
- [ ] **Spam Rate Limiter**
  JavaScript logic to disable the "Post" button for 60 seconds after a submission to prevent flooding.

- [ ] **Turnstile Gate (Comments)**
  Cloudflare Turnstile background verification required for the `/api/comment/post` call to pass.
---

## 🔍 6. Organic Growth (SEO)

- [ ] **Automated Sitemaps**
  Server-side script generating `sitemap.xml` daily based on MongoDB "Available" movies. Pings Google Console.

- [ ] **JSON-LD Schema**
  Injects "Movie" and "TVSeries" structured data into HTML `<head>` for rich search results.

- [ ] **Social Meta Tags**
  Dynamic OpenGraph (OG) images generation so shared links show the Movie Poster.

- [ ] **Ghost Library Logic (Programmatic SEO)**
  *   **Strategy:** Generate pages for movies/books *not* in our library yet (Status: Missing).
  *   **UI State:** Shows "Request This" button + Blurred Player instead of Video.
  *   **Data Source:** Scrape "Top 20,000" TMDB/MAL metadata.
  *   **Safety:** Only target "Upcoming" or "High Trend" titles to prevent user bounce.
    
- [ ] **Sitemap Proxy strategy**
  *   Since the Frontend is a Static Export (`output: 'export'`), it cannot generate dynamic sitemaps.
  *   **Logic:** `next.config.mjs` Rewrite rule: `/sitemap.xml` -> Proxy to `API_URL/sitemap.xml`. Backend generates the XML live from MongoDB.
     
## 📱 7. Layout Architecture & "Void" Aesthetics
*Goal: Replicate native desktop app feel (VoidAnime) on web, shrinking gracefully for mobile PWA.*

### A. Navigation Structure (Responsive)
*   **Desktop (The Sidebar):**
    *   **Style:** Vertical Left-Rail (Void Style). Icons only (collapsed) by default, expands glass panel on hover (Glassmorphism).
    *   **Placement:** Fixed `h-screen`, `z-index: 50`.
    *   **Items:** User Avatar (Top), Icons (Home, Browse, Schedule, Music), Settings (Bottom-Anchor) and a "Quick Player" status at bottom.
*   **Mobile (The Bottom Sheet):**
    *   **Style:** Fixed Bottom Navigation Bar (Glass effect).
    *   **Placement:** `bottom: 0`, `fixed`, safe-area inset compliant.
    *   **Behavior:** Auto-hides when scrolling *down* content, reappears on scroll *up* to maximize screen real estate.
    *   **Slots (5 Max):** `Home | Search | Schedule | Audio | Profile`.
    *   **The "Profile" Tab:** Acts as the menu wrapper. Clicking it opens a Sheet with Settings, Wishlist, Franchise Admin Link, and Login/Logout.

### B. Dashboard "Bento Grid" System
*   **Desktop:** Asymmetric CSS Grid (Big Blocks + Tall Sidebars).
*   **Mobile Adaptation:**
    *   **Grid Collapse:** Transforms 4-Column Grid into 1-Column Stack.
    *   **Priority Stacking:** 
        1. "Continue Watching" (Large Card).
        2. "Airing Today" (Horizontal Swipe Rail).
        3. "Trending" (Horizontal Swipe Rail).
    *   **Stats Block:** Moves to "User Profile" tab on mobile to declutter Home.

### C. Immersive Details Page (The "Sheet" Look)
*   **Desktop:** Full-viewport Background Image. Content sits in a Glass Panel on the left (`w-30%`).Tabs for [Episodes/Manga/OST] underneath
*   **Mobile:** 
    *   **Parallax Header:** Image takes top 45% of screen.
    *   **Draggable Sheet:** Metadata/Episodes sit in a "Bottom Sheet" that slides up over the image.
   *   **Navigation:** Swipe-able Tabs for Episode/Manga lists.
    *   **Thumb Zone:** "Play" and "Bookmark" buttons must be within easy reach of the thumb (bottom-right of header), not top-left.

### D. The "ShadowTunes" Player (Audio)
*   **Desktop:** Floating Glass Pill (Bottom-Right) or PIP visualizer.
*   **Mobile:** 
    *   **Mini-Player:** A thin 60px bar *floating 10px above* the Bottom Nav.
    *   **Interaction:** Swipe Down to hide, Tap to expand to Full-Screen "Cover Art + Lyrics Mode".

### G. Global Interaction States ("Zen Mode")
*   **Context:** Reading Manga or Watching Video on Mobile.
*   **Behavior:**
    *   **Input:** Single Tap on screen center.
    *   **Reaction:** Instantly slides **Navigation Bars (Top & Bottom)** away off-screen.
    *   **Goal:** True 100% full-screen consumption without UI distractions.

### H. The "Schedule" Calendar
*   **Desktop:** Full 7-Day Grid View (Horizontal days, Vertical time).
*   **Mobile:** 
    *   **Default:** Shows "Today's" episodes only as a list.
    *   **Interaction:** Horizontal Day Picker (Mon | Tue | Wed) sticky at the top to switch lists.
 
### I. Search & Filter UX
*   **Desktop:** Global Search Input in Sidebar or Top Right. Filters (Genre, Year) appear as sidebar or modal.
*   **Mobile:** 
    *   **Search:** Dedicated Tab in Bottom Nav.
    *   **Filtering:** "Chip Scroller" at the top (`[Action] [Adventure] [New]`).

------

## ✨ 8. Advanced UX Micro-Interactions (The "App" Feel)
*Goal: Remove "Website" behaviors (scrolling blankly) and replace with "Console" behaviors.*

### A. Ambient Mode (Idle State)
*   **Trigger:** Mouse/Touch inactivity > 60s (Configurable).
*   **Visual:** Cross-fading background carousel of High-Res "Fan Art" (sourced from TMDB/fanart.tv) related to User's active watchlist.
*   **Overlay:** Minimalist Clock + "Next Up: Solo Leveling (20m)" ticker at bottom left.
*   **Exit:** Any input restores full Dashboard.

### B. Custom Context Menus
*   **Desktop:** Override default browser Right-Click.
*   **Mobile:** Long-Press gesture.
*   **Menu Options (Context Sensitive):**
    *   *On Poster:* `[Quick Play]` `[Add to Collection]` `[Copy Share Link]`.
    *   *On Player:* `[Snapshot]` `[Fit to Screen]` `[Stats for Nerds]`.

### C. The "Module" Settings UI
*   **Design:** A grid of "Cards" representing features, simulating a Plugin Store.
*   **Toggles:**
    *   "NSFW Protocol" (Switch).
    *   "Data Saver Engine" (Switch).
    *   "Visualizer: Audio" (Switch).
*   **Theming:** Color picker and Font scale represented as graphical blocks, not dropdowns.

### D. Calendar Visualizer
*   **Style:** Horizontal Time-Stream.
*   **Indicator:** A vertical "Live Now" line moves across the grid based on user's timezone.
*   **Filters:** Switch between `[Global Release]` (Everything) vs `[My Library]` (Only shows I watch).

---

## 🌐 9. The Portal System (Unified Domains)
*Goal: Provide distinct visual experiences for Movies vs Anime without splitting domains/users.*

### A. The Gateway (Home / )
*   **Design:** A minimalist landing page containing 3 distinct "Hub Entrances". Animated Cards
*   **Card 1: 🎬 CINEMA:** Routes to `/cinema/` (Movies/Series). Visuals optimize for Horizontal Posters, Live-Action logic. Shows "Cast/Rotten Tomatoes". Logic: `genre != Animation`.
*   **Card 2: ⛩️ ANIME:** Routes to `/anime/` (Anime/Manga). Visuals optimize for Vertical Posters, Grid Schedules. Shows "Voice Actors/MyAnimeList". Logic: `genre == Animation`.
*   **Card 3: 🎵 TUNES:** Routes to `/tunes/` (Audiobooks/OSTs). Visuals optimize for Square Album art.
  
*   **Cookie Persistence:**
    *   When user selects a Hub, set cookie: `preferred_hub=anime`.
    *   **Next Visit:** Middleware redirects `/` -> `/anime` automatically (skipping the Gateway).
    *   **Switching:** "Exit" button in the Sidebar clears the cookie and shows the Gateway.

### B. Adaptive Navigation (Zustand State)
*   **Logic:** The Global Sidebar adapts its icons based on the Active Hub.
    *   *In Anime Hub:* The "Calendar" icon appears (for Simulcasts).
    *   *In Cinema Hub:* The "Collections" icon appears (for Marvel/DC universes).
    *   *Shared State:* Search, Profile, and Settings remain constant across all hubs.
 
*   **The Problem:** Global "Home" buttons usually link to root.
*   **The Fix:** The Navigation Component must subscribe to `useStore((state) => state.activeUniverse)`.
    *   **Cinema Mode:** Home Icon links to `/cinema`. Search defaults to "Movies".
    *   **Anime Mode:** Home Icon links to `/anime`. Search defaults to "Anime + Manga".
    *   **Music Mode:** Home Icon links to `/tunes`. UI switches to Audio Visualizer.
 
### C. Visual Identity Shifting
*   **Theme Engine:** Uses CSS variables mapped to the Universe.
    *   **Cinema:** Obsidian Black + Neon Cyan (`#00d8ff`).
    *   **Anime:** Deep Violet + Electric Purple (`#9d00ff`) + "Schedule" Icon appears.
    *   **Tunes:** Midnight Blue + Soundwave Yellow.

---

## 🗃️ 10. The Archive Page (Download Hub)
**Goal:** A centralized intermediate page for file hosting options, mirroring "ToonWorld4All" functionality.

*   **Route:** `/archive/{short_id}`.
*   **Header Info:** Shows content image, filename, specific file size (e.g., "850 MB"), and upload date.
*   **Host Grid:** Dynamic list of cards based on `file.downloads[]` from DB.
    *   Cards show: Provider Logo, Hostname, and CTA Button.
*   **Link Masking:** Buttons do NOT link directly to `mega.nz`. They link to `/api/shorten/redirect?target={url_id}` to ensure monetized click-through.
