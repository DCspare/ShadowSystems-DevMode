📂 Phase 2 Blueprint: Shadow Command (Admin Panel)

> **Filename:** `docs/v2_blueprint/context_06_admin_panel.md`<br>
**Role:** A web-based "God Mode" interface for managing content, users, revenue configurations, and infrastructure health.<br>
**Access:** Strict RBAC (Role Based Access Control) – restricted to users with `role: 'admin'` via JWT middleware.

---

## 🎨 1. UI/UX Architecture

**Design Philosophy: "Mission Control"**
Unlike the public facing "Cinematic" UI, the Admin Panel focuses on **Data Density** and **Action Speed**.
*   **Framework:** Next.js (App Router) -> `app/admin/layout.tsx` (Different layout from main site).
*   **Component Library:** `shadcn/ui` (Tables, Data Grids, Forms) + `ApexCharts` (Visualizations).
*   **Sidebar Navigation:** Dashboard, Library (Video/Manga), Users, Reports, Swarm, Settings.

**Security Middleware:**
*   **Route Protection:** Next.js Middleware (`middleware.ts`) intercepts `/admin/*`. Decodes JWT. If `role != admin`, immediate redirect to 404 (Security through obscurity).
*   **API Protection:** All `/api/admin/*` endpoints must strictly verify the `Admin_Secret` or JWT claims before executing database writes.

---

## 🧩 2. Core Functional Modules

### A. Live Dashboard (The Pulse)
*Visualization of Real-Time System Health.*
*   **Live Metrics:**
    *   **Active Concurrent Streams:** Live number from Redis counter.
    *   **Current Bandwidth Output:** Gauge chart (0Gbps -> 4Gbps).
    *   **CPU Load (Oracle):** Red/Green indicator fetched from Prometheus API.
*   **Business Intelligence:**
    *   **Revenue Estimates:** `(Download Button Clicks / 1000) * $3.50` (Charted daily).
    *   **User Growth:** Daily active users (DAU) vs New Signups.

### B. Library CMS (Content Management)
*Solving metadata errors without commands.*
*   **Unified Data Grid:** Tab switching between [Movies] | [Series] | [Books].
    *   *Features:* Sorting (by views), Search (by ID/Name), Batch Actions (Delete/Re-Index).
*   **Editor Modal:** Clicking a row opens a form:
    *   **Visuals:** Drag & Drop image replacer (proxies to Telegram Upload).
    *   **Files:** View linked Telegram IDs for "1080p", "4K", etc. Manually paste a new File ID if the auto-match failed.
    *   **"Fix Match":** Button to search TMDB/MAL again and forcibly overwrite metadata.
*   **Chapter Manager (ReadVault Specific):**
        *   Drill-down view to see all 100+ chapters of a series.
        *   Actions per Chapter: `[Purge Cache]`, `[Re-Leech]`, `[Delete]`.
    *   **Batch Ingest Tool:**
        *   Input box: "Paste Source URL (MangaDex/Manganato)".
        *   Action: Triggers Worker Swarm to index the whole series.

*   **Link Management:** Display the "Short Link" alongside the internal ID.
*   **Regenerate Button:** Ability to "Refresh Slug" if a specific short link gets mass-reported or flagged.

*   **Embed Health Status:**
    *   Visual indicators next to external links (e.g., `[VidHide: 🟢 Active]`, `[StreamTape: 🔴 Deleted]`).
    *   **Action:** `[Re-Upload Embeds]` button that triggers the Manager to grab the file from pixeldrain or other backup hosts and re-push it to the failed host.

*   **ShadowTunes Manager (Music Tab):**
        *   **Ingest Tool:** Input box for YouTube/Spotify Playlist URL.
        *   **Track Editor:** Drag & Drop sort order for Album tracks.
        *   **Metadata Fix:** Upload "Square" Album Art manually if the automated scrape gets low resolution.

*   **"Archive" Link Manager (Download Hub):**
        *   **UI:** A dedicated tab inside the Movie Editor Modal: `[ Streaming ] | [ Downloads ]`.
        *   **The Grid:** Lists all active mirrors for the Archive Page (PixelDrain, Gofile, Mega, HubCloud).
            *   *Columns:* Provider Icon | URL (masked) | Click Count | Status (🟢/🔴).
        *   **Actions:**
            *   `[Add Mirror]:` Paste a URL manually (e.g., if you manually uploaded to Mega).
            *   `[Batch Health Check]:` Pings all download links to see if the file was deleted by the host. If 404, marks status as `dead`.
            *   `[Daisy-Chain Upload]:` Trigger a background task to take the current Telegram file and remote-upload it to a specific host (e.g., "Upload to Gofile") to replenish dead links.

### C. Swarm Controller (Ingestion)
*Managing the Bots without Terminal access.*
*   **Worker Status Grid:** List of 10 workers showing "Idle", "Downloading", or "FloodWait" status.
*   **Active Queue:** See what content is currently downloading.
    *   **Actions:** `[Cancel Task]`, `[Prioritize]` (Move to top).
*   **Approvals:** If "Crowdsourced Ingestion" is on, list pending user submissions for one-click `[Approve/Reject]`.

- [ ] **Remote-Pull Ingest (Web UI):**
  *   **Feature:** Input field to paste Movie/Manga URLs (DDL, Torrent, Magnet).
  *   **Logic:** Signals Worker Swarm to download and index without Admin uploading bytes.
- [ ] **The "Gatekeeper" Dashboard (Review Queue):**
  *   UI to manage "Pending" uploads from Tenants. 
  *   **Actions:** `[Preview]`, `[Approve & Move to Log]`, `[Reject & Delete]` Notify to tenants.
- [ ] **Smart URL-to-Meta Matcher:**
  *   **Logic:** When a Remote URL/Magnet is pasted, the API parses the filename (PTN) and queries TMDB/MAL.
  *   **UI:** Displays a "Suggested Match" (Poster/Title) for confirmation before the download starts.
  *   **Goal:** Reduces manual data entry to a single "Confirm" click.
- [ ] **Sample Preview:** In the "ShadowExplorer" or Queue, show the Sample Video if available (faster/cheaper to verify than streaming the 2GB file via proxy).
      
### D. User Management (CRM)
*Support & Safety controls.*
*   **Search:** Find user by ID, Magic Link Token, or IP Address.
*   **Security Operations:**
    *   `[Reset Device Lock]`: Unlocks an IP-Bound session (fixing the "Potato Laptop" handover issue manually).
    *   `[Ban User]`: Revokes access token + blacklists IP.
*   **Credits:** Button to manually `[Grant Premium]` (7 Days / 1 Month) for winners/friends.

### E. The Medic Center (Reports)
*Handling Broken Links.*
*   **Kanban View:** `Pending` -> `Repairing` -> `Fixed`.
*   **Diagnostic Action:**
    *   Button `[Test Link]` tries to fetch the first byte from backend.
    *   Button `[Re-Leech]` sends the ID back to the Worker Swarm to re-download.
    *   Button `[Switch to Backup]` force-swaps the Primary Link to the Abyss.to mirror.

### F. System Settings (Hot-Swappable Config)
*Change business logic without re-deploying code.*
*   **Ad Network Keys:** Input fields for GPlinks API Token, Adsterra Codes. Updates Redis config instantly.
*   **Mode Toggles:**
    *   `Maintenance Mode`: Up/Down.
    *   `Guest Access`: Allow/Deny.
    *   `18+ Filter`: Strict/Loose.
*   **Domain Switcher:** Update the `BASE_URL` if you change domains to ensure Magic Links generate correctly.
*   **File Manager** capability:
    *   `[Upload New cookies.txt]` -> Overwrites the file in the shared Docker Volume.
    *   `[Update Torrent Trackers]` -> Updates the list passed to `aria2c`.

> (You don't need to regenerate files for this; just keeping it in mind ensures you build a "Control Panel" that saves you from SSHing into the server every month).

*   **Config Loader (Rclone):**
    *   **UI:** A "Paste Config" text area for the contents of `rclone.conf`.
    *   **Backend:** Writes this content to the shared `/app/config/rclone.conf` file used by the Worker Swarm and Manager.
    *   **Status Check:** Button to run `rclone listremotes` to verify connection to the Backup Drive (e.g., Mega).

### G. Franchise Master Control (B2B CRM)
*Management interface for the "Shadow Systems" business side.*
*   **Tenant Overview Grid:**
    *   Columns: Domain Name | Plan (Partner/Tycoon) | Status (Green/Red) | **Next Bill Date**.
    *   **Traffic Sparkline:** A mini graph showing last 7 days visits per site.
*   **Detailed View:** Clicking a tenant opens their full profile.
    *   **Resource Manager:** Dropdown to manually assign/revoke specific `worker_ids` to them.
    *   **Subscription Control:** [Extend 30 Days] | [Suspend Site] | [Add Note].
    *   **Add-on Toggle:** Checkboxes to activate/deactivate "Android App" or "DMCA Shield" status in DB.

---

## 🔗 3. Connectivity (API Specs)

The Admin Panel frontend communicates with the **Manager Bot API** (FastAPI) via dedicated routes.

| Method | Endpoint | Function |
| :--- | :--- | :--- |
| `GET` | `/api/admin/stats/live` | Fetches Prometheus + Redis counters. |
| `GET` | `/api/admin/library/search?q=...` | Mongo Full-Text search. |
| `POST` | `/api/admin/content/update/{id}` | Updates metadata or file links in Mongo. |
| `POST` | `/api/admin/system/purge-cache` | Triggers Cloudflare + Nginx Cache wipe for specific ID. |
| `POST` | `/api/admin/swarm/cancel/{task_id}` | Signals Worker Bot to `task.cancel()`. |

---
