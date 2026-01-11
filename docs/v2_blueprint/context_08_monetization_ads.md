📂 Phase 4 Blueprint: Monetization & Ad Implementation<br>
> **Filename:** `docs/v2_blueprint/context_08_monetization_ads.md`<br>
**Role:** Defining the Revenue Stack (Ads, Shorteners) and their placement strategy across StreamVault and ReadVault.<br>
**Primary Partners:** Adsterra (Passive Ads) & GPlinks (Active Action Locks).

---

## 💰 1. The Ad Stack Strategy (Partners)

We separate monetization into two layers: **"Traffic Volume"** (Views) and **"Action Value"** (Downloads).

### A. High-Volume Layer (Passive) -> **Adsterra**
*   **Role:** Earns from clicks, pop-unders, and views on the website.
*   **Payout:** USDT (Tether) / Bitcoin / Wire.
*   **Why Selected:** High CPM for Indian traffic, crypto payouts (privacy), and aggressive "Social Bar" formats.

### B. High-Value Layer (Active) -> **GPlinks**
*   **Role:** Subsidizes the cost of heavy server actions (4K Video, Zip Packs, CBZ Downloads).
*   **Payout:** UPI (PhonePe, Paytm, GPay) or Bank Transfer.
*   **Why Selected:** Highest consistent rate for India ($4-$5), reliable UPI payouts, stable uptime.

---

## 📍 2. Placement Strategy (The Heatmap)

We do not use a "one size fits all" approach. Video watchers and Manga readers behave differently.

### 🎥 StreamVault (Video Optimization)
*   **Pop-Under (Primary):** Triggers on the **Video Play** button click.
    *   *Frequency Rule:* Max 1 pop every 45 minutes per user session.
    *   *Why:* Users expect it on streaming sites. It pays the most.
*   **Social Bar (Floating):** A fake "Notification Bubble" (e.g., *VPN Update*, *Dating App*) in the bottom-right corner.
    *   *Placement:* Global (Home, Search, Title Page).
    *   *Hide Condition:* **HIDDEN** automatically when Video Player enters Fullscreen.
*   **Native Banner (728x90):**
    *   *Placement:* Directly **Below** the Video Player component (Desktop Only).
    *   *Mobile Rule:* **Disabled** on Mobile to save screen space.

### 📖 ReadVault (Manga Optimization)
*   **Native Banners (300x250):**
    *   *Placement:* 
        1. Top of the Chapter List (Book Page).
        2. Top of the Reader (Before Image 1).
        3. Bottom of the Reader (After Last Image).
*   **The "Interstitial" (Gold Mine):** 
    *   *Trigger:* User clicks "Next Chapter".
    *   *Action:* Screen fades to black -> Shows Full Page Ad -> Wait 3 Seconds -> Loads Next Chapter.
    *   *Why:* Manga users read 20 chapters in a row. This creates 20 high-value impressions per session.

---

## 🛠️ 3. Technical Implementation

### A. Handling Pop-Unders (The React Way)
Don't just paste script tags. Control them so they don't break the React Lifecycle.

```javascript
// Component: components/ads/AdsterraPopunder.tsx
'use client';
import { useEffect } from 'react';

export default function AdsterraPopunder() {
  useEffect(() => {
    // 1. Check AdBlock Detection
    if (typeof window.canRunAds === 'undefined') return;

    // 2. Frequency Capping (Session Storage)
    const lastPop = sessionStorage.getItem('last_ad_pop');
    const now = Date.now();
    const COOLDOWN = 30 * 60 * 1000; // 30 Minutes

    if (!lastPop || now - parseInt(lastPop) > COOLDOWN) {
        // INJECT SCRIPT LOGIC HERE
        // ... adsterra code ...
        
        sessionStorage.setItem('last_ad_pop', now.toString());
        console.log('[Ads] Pop-under triggered');
    }
  }, []);

  return null; // Invisible Component
}
```

### B a. Handling Shorteners (The Gateway Logic)
Used for **"Download Season Pack"** or **"4K Source"**.

1.  **User Action:** Clicks "Download Pack".
2.  **Backend:** Checks Request.
3.  **Generator:** Manager API calls GPlinks API.
    *   `GET https://gplinks.in/api?api=KEY&url=https://shadow.xyz/api/verify_download?token=temp_jwt`
4.  **Redirect:** Frontend sends user to the *Shortened Link*.
5.  **Completion:** User solves Captcha -> Returns to `verify_download`.
6.  **Unlock:** Backend verifies token -> Sets `download_cookie` (Valid 1 hour) -> Redirects to actual Zip Stream.

### B b. The "/archive" Redirector API
*Dedicated endpoint for the Download Hub page (`/archive`).*

**Endpoint:** `GET /api/shorten/redirect?target={encrypted_url_id}`

**Logic Flow:**
1.  **Lookup:** Backend decrypts/looks up the real target URL (e.g., `gofile.io/...`) from MongoDB.
2.  **Safety Check:** Verifies the destination domain is in our "Allowed Mirrors" list (Prevents open redirect vulnerabilities).
3.  **Shortening Strategy:**
    *   *Ad-Block Check:* Optional header check.
    *   *Provider Selection:* Can rotate between GPlinks/ShrinkMe if configured (Load balancing revenue).
    *   *API Call:* Sends Target URL to `SHORTENER_API_URL` (from Env).
4.  **Redirect:** Returns a `302 Found` header sending the user to the `gplinks.in/xyz` result.

### C a. VAST Video Ads (The "TV Experience")
*Implemented directly inside the Video Player logic, independent of the page layout.*

**1. The Logic:**
We use **Adsterra VAST XML** tags.
*   **Pre-Roll (Start):** Mandatory. Plays immediately when user clicks Play.
    *   *Skip Logic:* Set to "Skippable after 5 seconds" (Configured in Player).
*   **Mid-Roll (Middle):** Optional.
    *   *Trigger:* If movie duration > 45 minutes, insert 1 ad slot at 50% timestamp.
    *   *Warning:* Mid-rolls can annoy users during tense scenes. Use sparingly.

**2. Player Integration (ArtPlayer):**
Do not use Google IMA SDK (it bans piracy sites). Use ArtPlayer's native VAST plugin.
```javascript
// Example Config for Frontend Developer
const art = new ArtPlayer({
    // ... basic config ...
    plugins: [
        artplayerPluginVast({
            ad: [
                {
                    // Get this URL from Adsterra "Direct Link / VAST" section
                    url: 'https://ad-network.com/vast.xml?key=YOUR_KEY',
                    startTime: 0, // Pre-roll
                    type: 'video',
                },
                {
                    url: 'https://ad-network.com/vast.xml?key=YOUR_KEY',
                    startTime: '50%', // Mid-roll (Halfway through)
                    type: 'video',
                }
            ],
        }),
    ],
});
```
### C b. VAST Video Ads (The "Buffer Shield")
*Using Ads to mask server latency while earning higher CPM.*

**1. The "2-Second Rule" (Timeout Protection)**
*   **Problem:** Ad servers can be slow. If an ad takes 10s to load, the user leaves.
*   **Logic:**
    1.  Player requests VAST XML. Start Timer.
    2.  **IF** Ad loads within 2000ms (2s) -> Play Ad.
    3.  **IF** Timer hits 2s (Timeout) -> **Abort Ad Request**. Trigger "Play" on main video immediately.
    4.  **IF** AdBlock detected -> **Abort**. Trigger Pop-under fallback.

**2. The "Background Pre-load" Strategy**
*   **Concept:** Use the ad playback time to buffer the main movie.
*   **Implementation:**
    *   When VAST Ad starts (`event: ad_start`):
    *   **Force Trigger:** JavaScript sets `video.preload = "auto"` on the main content element.
    *   **Result:** While user watches the 15s Ad, the browser downloads the first ~20MB of the 4K movie.
    *   **Benefit:** When Ad ends, Movie starts with **0ms latency** (Buffer is already full).

**3. Anti-Blocker Strategy:**
*   VAST ads are often blocked by uBlock Origin.
*   **Fallback:** If the VAST XML fails to load (network error), the Player `onError` event must trigger the **Pop-under Script** immediately as a backup. This ensures you always get paid.

---

## 🛑 4. Anti-AdBlock Rules (Revenue Defense)

We apply different penalties based on *where* the user is blocking us.

| Tier | Condition | Consequence |
| :--- | :--- | :--- |
| **Tier 1** | **Banner** Blocked | **Passive Toast:** "We lost a banner ad. Please help us." (User can close). |
| **Tier 2** | **Shortener** Blocked | **Critical Failure:** Shortener Site will likely block the user entirely. We do nothing; GPlinks handles the lockout. |
| **Tier 3** | **Pop-under** Blocked | **Content Lock:** If "Pop-under Script" fails to load on the Video Player -> Show Modal: *"AdBlock Detected. Video functionality paused."* (15s timer). |

### The "Honeypot" Script
Ensure `public/js/ads_core.js` exists with:
```javascript
// A fake ad variable that AdBlockers will kill
var canRunAds = true;
```
If `window.canRunAds` is `undefined`, we know they are blocking.

---

## 🧾 5. Payout Workflow (India)

Since you are a "Company of One" in Phase 1, efficient cash flow is vital.

*   **Daily Earnings:** GPlinks accrues INR. Adsterra accrues USD.
*   **Weekly Workflow:**
    1.  **GPlinks:** Withdraw > ₹500 via **UPI** directly to Bank Account. (Pays Server costs).
    2.  **Adsterra:** Wait for $100 threshold (Net-15). Withdraw via **USDT (TRC20)** to Binance/Bybit.
        *   *Action:* Sell USDT on P2P Market for INR to Bank Account.
*   **Profit Allocation:**
    *   **30%**: Server Savings (Buying bigger Hetzner/Oracle quotas).
    *   **20%**: Domain/Proxy Costs (Cloudflare).
    *   **50%**: Growth (Buying Phone Numbers for Swarm, Marketing).

---

## ☁️ 6. Passive Backend Revenue (PPD Model)
*Earning from the infrastructure itself (Backup Mirrors).*

### The "Mirror" Strategy
Since we upload backups to **PixelDrain** and **StreamWish** (via Remote Upload), we enable their Affiliate/PPD programs.
*   **Priority Logic:** If the User selects "Server: Backup 1 (Fast)" or downloads via Mirror:
    *   The User gets the file.
    *   **We get PPD Credit** on the hosting platform ($2-$10 / 10k views).
*   **Scale:** With 10,000 daily file hits, this covers the cost of buying premium Telegram numbers without active effort.

### Abyss.to PPD Integration
*   **Role:** Dedicated Streaming Backup.
*   **Automation:** Utilize "Remote Upload" via PixelDrain links to populate Abyss library without VPS bandwidth usage.
*   **Revenue:** Earn through Abyss PPD ($5 - $30 per 10k views depending on country).

---

## ☕ 7. Donations & Community Support
*Direct value transfer from "Super Fans" who hate ads.*

### The "Support" Page (`/support`)
A static glass-UI page reachable via Footer.
*   **Methods:**
    *   **UPI QR Code:** (Static image) "Scan to buy us a server coffee."
    *   **USDT (TRC20) Address:** For anonymous crypto support.
    *   **Motivation:** "100% of donations go to buying more hard drives and worker bots."
*   **No Paywalls:** This is purely voluntary. We do not use "Donation locked" content (to avoid legal payment processor scrutiny).

## 💎 8. The Freemium Value Proposition
**Goal:** Convert Free Users (Cost) into Premium Users (Profit) by leveraging Server Quality.

### The "VIP Pass" ($2 / Month or Crypto)
*   **Ad-Free Experience:** Removes Shadow Systems Pop-unders and Banners.
*   **VIP Server Access:** Unlocks the **ShadowStream (Telegram)** player.
    *   *Why users pay:* To escape the aggressive ads and buffering of VidHide/StreamTape.
*   **Bandwidth Logic:** Premium users fund the Oracle/VPS expansion. Free users cost $0 (served by Embeds), but we'll still get revenue by pop-under or banner ads.

## 🎟️ 9. The "Shadow Pass" (Time-Wall Model)
*Inspiration: Tooniboy. Trade "1 Action" for "12 Hours of Peace".*

### A. The Offer
A specific modal triggered when Guest users try to access **VIP Features** (4K, Oracle Server, Batch Downloads).
*   **Proposition:** "Verify you are human to unlock VIP Server + Ad-Free Mode for 12 Hours."
*   **Action:** User solves 1 Shortener Link (GPlinks).

### B. The Mechanism (Stateless JWT)
1.  **Generation:** Backend wraps a self-verifying Callback URL inside a Shortener API call.
2.  **Verification:** Upon return, Backend sets a `shadow_pass` Secure Cookie valid for **43,200 seconds (12h)**.
3.  **Privilege:** Middleware checks for this cookie. If present -> Disable Pop-unders, Disable VAST, Enable Oracle Streaming.

### C. Financial Upside
*   **Revenue Ratio:** 1 Pass Unlock = ~15 standard Pop-under views.
*   **UX Benefit:** Users prefer doing "one hard task" to get "peace," increasing retention vs. sites that spam ads constantly.

---

## ✅ The Full Revenue Picture & Integration Checklist.

File covers all **4 Pillars of Revenue**:

1.  **Views:** Adsterra (Social Bar / Pops).
2.  **Actions:** GPlinks (Zip/CBZ Downloads).
3.  **Storage:** PPD (PixelDrain Mirror streams).
4.  **Goodwill:** Donations (UPI/Crypto).

---

- [ ] **1. Sign Up:** Create accounts on Adsterra (Publisher) and GPlinks.
- [ ] **2. Code Verification:** Verify your `.xyz` domain ownership with Adsterra (DNS method).
- [ ] **3. Env Secrets:** Add `ADSTERRA_PID` and `GPLINKS_API` to your `.env` (via Admin Panel config).
- [ ] **4. React Hooks:** Build the `useAds()` hook to centralize the Frequency Capping logic across the entire Frontend.
- [ ] **5. Testing:** Test ad injection with AdBlock **OFF** and **ON** to ensure the defense messages appear correctly.
