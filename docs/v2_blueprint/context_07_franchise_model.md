📂 Phase 4 Blueprint: The Franchise Model (SaaS)<br>
> **Filename:** `docs/v2_blueprint/context_07_franchise_model.md`<br>
**Role:** Transitioning from a single consumer website to a "Streaming-as-a-Service" Platform provider.<br>
**Goal:** Selling the technology/library to other webmasters while protecting the core infrastructure.

---

## 🏛️ 1. Architecture: Multi-Tenancy

We do not spin up new containers for every client. We use a **Single Monolith Architecture** with **Middleware Routing**.

### The Next.js Middleware Logic
1.  **Request Inbound:** Traffic hits `custom-movie-site.com`.
2.  **DNS Routing:** Domain points to your Oracle Cloudflare Origin.
3.  **Lookup:** Backend checks the `tenants` collection: *"Who owns custom-movie-site.com?"*
4.  **Asset Switch:**
    *   Loads Tenant Config (Logo, Brand Name, Primary Colors).
    *   Loads Tenant DB Prefix (Separate User Auth tables).
    *   Loads Global Library (Shared Movies/Books).
5.  **Result:** The user sees a unique site. The server runs the same optimized code.
   
*   **Domain Shielding:** Franchisees get their own "Short Link" domains (e.g., `watch.tenant-site.com/v/XYZ`).

---

## 💰 2. Franchise Structure (The Pricing)

To protect the "Black Box" nature of the backend, all plans require a **One-Time Provisioning Fee**. This fee creates the illusion of server setup costs while actually covering the cost of Admin purchasing fresh Worker Numbers ($2).

**Universal Setup Fee:** **$50 (One-time, Crypto)**.
*   *Justification to Client:* "Server instantiation, Database shards, and CDN allocation."
*   *Actual Use:* buying 3-5 high-quality Telegram sessions (~$2) + Profit ($48).

### Plan A: The "Growth Partner" (Revenue Share)
*   **Target:** Marketing experts with limited budget.
*   **Monthly Fee:** **$0 / Month**.
*   **Revenue Split:** **70/30**.
    *   *Client:* Keeps 70%.
    *   *Shadow Systems:* Takes 30% via script injection (We inject our Pop-under tag into 3 out of every 10 clicks).
*   *Pros:* Zero maintenance cost for them. Perpetual passive income for you.

### Plan B: The "Tycoon" (White Label SaaS)
*   **Target:** Established brands wanting 100% control.
*   **Monthly Fee:** **$50 / Month**.
*   **Revenue Split:** **0%** (Client keeps 100%).
*   *Features:* "Powered by" branding removed. Priority Support.
*   *Pros:* Predictable monthly cash flow.

---

## ⚙️ 3. Operational Requirements

### The Managed Infrastructure Protocol
We **never** ask clients for API keys or Phone Numbers. This exposes that we run on Telegram. Instead, we sell "Slots".

1.  **Provisioning (Manual Step):**
    *   Client pays Setup Fee ($50).
    *   **Admin Action:** Admin goes to SMS Marketplace, buys 3 Telegram numbers (~$1.50), and logs them into the Worker Hive.
    *   **Assignment:** Admin tags these new sessions in the database with `owner: tenant_id`.
2.  **Resource Quota:**
    *   Each Tenant gets a dedicated "Bandwidth Pool" (assigned workers).
    *   If their site goes viral and buffers, Admin can offer "CDN Upsell" -> Buy more workers for $10/setup to expand capacity.
3.  **Traffic Isolation:**
    *   Requests from `tenant-domain.com` are strictly routed through their assigned Workers only. This prevents a flood-ban on one partner from affecting the Main ShadowStream site.

### Content Control (Quality Assurance)
*   **Read-Only Library:** Franchisees **cannot** directly upload/delete files (avoids malicious uploads).
*   **Request Queue:** Franchisees have a "Priority Request" button in their dashboard. The Core Admin (You) approves the Leech. This maintains Library purity.

---

## 💾 4. Database Schema Extensions

### Collection: `tenants`
```json
{
  "_id": "tenant_x99",
  "domain": "anime-hub.com",
  "owner_email": "client@gmail.com",
  "plan": "rev_share",                // rev_share | fixed_fee
  
  // 🎨 BRANDING
  "config": {
    "site_name": "AnimeHub",
    "logo_url": "https://...",
    "primary_color": "#ff0000",
    "show_18_plus": false             // Option to act as a "Family Safe" site
  },

  // 💰 MONETIZATION
  "ad_codes": {
    "popunder": "<script>...", 
    "banner_home": "<script>..."
    "vast_tag": "https://ad-network.com/vast?id=123" // VAST XML Link
  },
  
  // 🚜 MANAGED RESOURCES (Internal Admin Use Only)
  "resource_pool": {
      "worker_ids": ["worker_id_5", "worker_id_6"],
      "bandwidth_tier": 1,        // 1=Standard (3 bots), 2=High (10 bots)
      "worker_status": "active"   // If flood-banned, marks site as "degraded"
  },

  // ➕ Add-on Tracking (Billing & Features)
  "addons": {
    "android_app": {
      "is_active": true,
      "apk_url": "https://cdn.shadow.xyz/builds/animehub.apk",
      "last_built": ISODate("...")
    },
    "dmca_shield": {
      "is_active": false,
      "proxy_ip": null        // Assigned when they pay the $15/mo
    },
    "capacity_boost": {
      "purchased_units": 2    // How many extra sets of workers they bought
    }
  },
  
  // 📆 SUBSCRIPTION STATUS
  "next_billing_date": ISODate("2026-02-01"),
  "auto_suspend_if_unpaid": true
}
```

### Updates to: `users`
*   New Field: `tenant_id` (String).
*   *Logic:* A user registered on "Site A" cannot log in to "Site B", even though they share the same physical database.

---

## 🔒 5. Franchisee Admin Panel
Accessible via `client-domain.com/admin` (Limited View).

### The Tenant Dashboard
*   **Subscription Widget:** 
    *   Display: **"Current Plan: Tycoon"**.
    *   Countdown: "Renewal in: 14 Days" (Green) or "Expired" (Red).
    *   Upgrade Button: Links to your payment/support page for Add-ons.
*   **Site Analytics (Filtered):**
    *   We specifically filter logs by `host == tenant_domain` to show them *only* their traffic.
    *   **Metrics:** Top Viewed Movies (on their site), Total Visitors, Device breakdown.
*   **Config Center:**
    *   **Ad Manager:** Simple input boxes to paste their specific Adsterra/GPlinks Codes.
    *   **Branding:** File Uploader for "Site Logo" and Color Picker for "Accent Color."
    *   **User Manager:** Ban/Reset users specifically registered to their domain.
*   **Capabilities BLOCKED:**
    *   Access to Global Worker Settings.
    *   Deleting Content from Library.
    *   Viewing Global System Stats.

*   **VAST Ad Input:** A dedicated field for tenants to paste their **Adsterra VAST XML link**. 
*   **Benefit:** This "Activates" their player monetization instantly without them needing to touch code.

- [ ] **Cloud-Ingest Tool:**
  *   Allows Tenants to grow their own library sections via Remote URLs.
  *   **Constraint:** All Tenant uploads enter "Quarantine" and require Super-Admin approval before appearing live.
- [ ] **Automated Metadata Fetcher:**
  *   Franchisees only need to provide a link; the system auto-populates plots, cast, and posters.
  *   **Safety:** Prevents franchisees from messing up the Global Library with bad titles or typos.
---

## 🛡️ 6. Tech Stack & Safety Protocols (Legal Isolation)

1.  **DNS Isolation:**
    *   Tenant domains are **never** hosted on your Cloudflare account.
    *   They must add the domain to *their* Cloudflare and point CNAME to your backend.
    *   *Reason:* If they get DMCA-banned by Cloudflare, it does not affect your master account.
2.  **No Direct Linking:**
    *   They never get the Raw Telegram Files. Everything proxies through your API via the Tenant Token. You can "Kill Switch" a tenant instantly if they break rules (e.g., uploading illegal content/spam).

### The "App Builder" Stack (Bubblewrap CLI)
To fulfill the **$10/mo Android App** upsell without manual coding:
*   **Tooling:** Use **Google Bubblewrap** (CLI Node.js tool) to wrap the PWA into a TWA (Trusted Web Activity).
*   **Workflow (Admin Localhost):**
    1.  **Config:** Maintain a `twa-config.json` for each Tenant (Logo, URL, Theme Color).
    2.  **Build Command:** `bubblewrap build --manifest=https://tenant.com/manifest.json`.
    3.  **Signing:** Auto-sign the APK using a generic "Shadow Keystore".
    4.  **Delivery:** Upload the resulting `.apk` to PixelDrain and email the link to the Tenant.
*   *Note:* This process is run locally by the Admin or via GitHub Actions, NOT on the Oracle Server (to save RAM/Disk).

---

## 🛒 7. Appendix A: The Sales Interface (Landing Page Design)
*Design Reference: Netflix / Vercel Pricing Page.*

**Headline:** "Start Your Streaming Empire."
**Sub-headline:** "We provide the Tech & Content. You provide the Audience."

### 1. The Core Plans
*Displayed as comparison cards with Toggle: [Monthly / Yearly].*

| Features | **THE PARTNER** (Growth) | **THE TYCOON** (SaaS) |
| :--- | :---: | :---: |
| **Setup Fee** | **$50** (One-time) | **$50** (One-time) |
| **Monthly Cost** | **$0 / month** | **$50 / month** |
| **Revenue Model** | **70/30 Split**<br>*(You keep 70% of Ads)* | **100% Yours**<br>*(We take 0% Commission)* |
| **Ideal For** | Marketers & Influencers | Established Site Owners |
| **Library Access** | 📺 Full 10TB+ (Movies/Shows)<br>📖 Full Manga/Manhwa DB | 📺 Full 10TB+ (Movies/Shows)<br>📖 Full Manga/Manhwa DB |
| **White Label** | "Powered by Shadow" in Footer | **100% Invisible Branding** |
| **Worker Capacity** | Standard (3 Slots) | Standard (3 Slots) |
| **Action** | **[ START PARTNER ]** | **[ GO TYCOON ]** |

---

### 2. 📦 Upsells & Add-ons (Checkout Bump)
*Optional revenue boosters offered during the checkout process.*

#### 📱 **Android App Generation (+$10/mo)**
*   **Pitch:** "Get a downloadable `.APK` for your site to increase user retention."
*   **The Backend Reality:** Automated wrapper for the PWA. High perceived value, zero maintenance.

#### 🛡️ **DMCA Bulletproof Shield (+$15/mo)**
*   **Pitch:** "Hide your real domain IP behind our Offshore Reverse Proxy network. Ignore 99% of complaints."
*   **The Backend Reality:** Routes their custom domain through our cheap $2 AlexHost/Hetzner Nginx proxy before hitting the main Oracle server.

#### ⚡ **Capacity Boost (+$15 One-time)**
*   **Pitch:** "Add +2 Dedicated Workers to your fleet for faster speeds during viral spikes."
*   **The Backend Reality:** Admin spends $1 to buy 2 more Telegram numbers and assigns them to the tenant. Profit: $14.

---

## 📋 8. Deployment Phase Checklist

- [ ] **Phase 1:** Update `apps/web/middleware.ts` to detect `hostname` and fetch Tenant Config from DB.
- [ ] **Phase 2:** Update Manager Bot to accept `tenant_id` parameter in authentication routes.
- [ ] **Phase 3:** Create "Franchise Dashboard" layout (a subset of `apps/manager` frontend).
- [ ] **Phase 4:** Build the "Rev-Share Injector" (Random number generator for Ad scripts).

---

**Approval:** This context file provides the roadmap for turning the software into a B2B product after you have achieved success with your own domains.
