📂 Phase 3 Blueprint: ShadowTunes (Music Engine)
> **Filename:** `docs/v2_blueprint/context_11_music_engine.md`
**Role:** Extension for Streaming Audio, OSTs, and Background Music.
**Tech Stack:** `yt-dlp` (Ingestion), `mutagen` (Tagging), `Zustand` (Frontend State), `MediaSession API` (OS Integration).

---

## 🎧 1. Architecture & Data Flow

We leverage the existing **Video Worker** (which already contains `ffmpeg` and `yt-dlp`) to handle audio tasks, rather than creating a new container.

### The Pipeline
1.  **Input:** Admin/User provides a YouTube Music / Spotify Playlist URL.
2.  **Extraction:** Worker uses `yt-dlp --extract-audio --audio-format mp3`.
3.  **Enhancement:**
    *   Fetches High-Res Album Art (Square).
    *   Uses `mutagen` library to inject ID3 Tags (Artist, Title, Year, Cover).
    *   *Why:* Ensures the file looks professional if downloaded to a local device.
4.  **Storage:** Uploads individual tracks + One "Complete Album Zip" to **`TG_MUSIC_CHANNEL`**.
5.  **Streaming:** The Go Stream Engine pipes the Telegram bytes to the Frontend (`<audio>` tag).

---

## 💾 2. Database Schema Extensions

**Collection:** `music` (Linked to Movies/Anime)
```json
{
  "_id": "ost_interstellar_deluxe",
  "linked_tmdb_id": "tmdb_157336",  // The Hook to the Movie Page
  "type": "album",                  // album | playlist | single
  
  "title": "Interstellar: Original Motion Picture Soundtrack",
  "artist": "Hans Zimmer",
  "release_year": 2014,
  "cover_image": "AgAD...",         // Telegram File ID (High Res)
  "dominant_color": "#1a1a1a",      // Extracted from cover for UI theming
  
  // 📉 METRICS
  "plays": 15400,
  "likes": 850,

  // 📀 TRACKLIST
  "tracks": [
    {
      "track_num": 1,
      "title": "Dreaming of the Crash",
      "artist": "Hans Zimmer",      // Allows per-track artist overrides
      "duration": 235,
      "telegram_file_id": "CQACAg...",
      "stream_url": "/api/stream/audio/{file_id}" 
    }
  ],
  
  // 💰 MONETIZATION (Shortener Link)
  "zip_file_id": "BQACAg...",       // Pre-zipped Album
}
```

---

## 🏗️ 3. Backend & Worker Logic

### A. Worker Config Updates
*   **Requirements:** Add `mutagen` to `apps/worker-video/requirements.txt` for metadata manipulation.
*   **Env:** Add `TG_MUSIC_CHANNEL_ID` to `.env` file.

### B. Stream Engine Update (Go)
The current video engine handles `video/*` well. It must be updated to serve correct Audio MIME types to prevent Safari/iOS playback failures.
*   **Logic:**
    *   Detect File Header (Magic Bytes).
    *   If Audio: Send header `Content-Type: audio/mpeg` (for MP3) or `audio/flac`.
    *   Enable **Range Requests** (Critical for seeking audio timeline).

---

## 🎨 4. Frontend: The "Global Player"

### A. Architecture: "The Persistent State"
The Audio Player **cannot** live inside a Page Component (it would stop when you click a link). It must live in the **Root Layout**.

*   **State Manager:** Use **Zustand** (Library).
    *   `useMusicStore.ts` -> `{ currentTrack, playlist, isPlaying, volume }`
    *   Allows any page to command the player: `setTrack(newTrack)`.

### B. UI Components
1.  **Mini-Player (The Pill):**
    *   **Desktop:** Floating Glass Pill (Bottom Right).
    *   **Mobile:** A slim 64px Bar *fixed above the Bottom Navigation*.
    *   **CSS Rule (Mobile):** When `isPlaying === true`, inject `padding-bottom: 120px` to the `<body>` so the player doesn't cover the navigation tabs or content.
2.  **Full-Screen Mode (Lyrics/Vibe):**
    *   Expands on tap.
    *   **Background:** Dynamic blurred version of Album Art.
    *   **Visualizer:** Uses Web Audio API to render a simple "Bar Visualizer" reacting to frequencies.

### C. OS Integration (Lock Screen Controls)
**Critical for Mobile retention.** We must implement the **MediaSession API**.

```javascript
// On Play Trigger
if ('mediaSession' in navigator) {
  navigator.mediaSession.metadata = new MediaMetadata({
    title: track.title,
    artist: track.artist,
    artwork: [{ src: track.coverUrl, sizes: '512x512', type: 'image/png' }]
  });

  navigator.mediaSession.setActionHandler('play', () => audio.play());
  navigator.mediaSession.setActionHandler('pause', () => audio.pause());
  navigator.mediaSession.setActionHandler('nexttrack', () => playNext());
}
```

---

## 💰 5. Monetization Strategy (ShadowTunes)

Since we cannot put video ads inside an Audio stream effectively (users hate audio ads), we monetize the **Context** and the **Asset**.

### A. "Download Quality" Gate
*   **Stream Quality:** 128kbps AAC (Standard). Good for streaming.
*   **Download Quality:** 320kbps MP3 / FLAC (Audiophile).
*   **Action:** The **"Download Album (ZIP)"** button routes through **GPlinks** (Shortener).
    *   *Pitch:* "Support the site & Get FLAC Quality."

### B. Passive Ad Space
In the **Full Screen Player Mode** (which users stare at for Lyrics or Vibes), place a discrete **300x50 Banner Ad** (Adsterra) directly below the Seek Bar controls.

---

### ✅ Deployment Checklist

- [ ] **Infrastructure:** Update `docker_compose` to map the `mutagen` cache if needed (usually handled in temp).
- [ ] **Environment:** Create the Music Channel on Telegram.
- [ ] **Frontend:** Install `zustand` and update `layout.tsx` to include the `<GlobalAudioPlayer />`.
- [ ] **Stream Engine:** Recompile Go binary with Audio MIME type detection logic.
