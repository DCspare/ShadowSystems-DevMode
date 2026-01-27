📂 Phase 2 Blueprint: Master Database Schema<br>
> **Filename:** `docs/v2_blueprint/context_04_database.md`<br>
**Role:** Definitive JSON Schemas for MongoDB (Atlas) ensuring compatibility between StreamVault (Video) and ReadVault (Manga).

---

## 📽️ Collection: `library` (Movies, Series & Books)
*A unified collection handled by the Manager Bot to populate the website catalog.*

### A. Movie Entity
```json
{
  "_id": "tmdb_299534",             // Primary Key
  "short_id": "v7K1wP2",          // 7-character Base62 Slug
  "media_type": "movie",            // movie | series | manga
  "title": "Avengers: Endgame",
  "clean_title": "avengers endgame",
  "year": 2019,
  "genres": ["Action", "Sci-Fi"],
  "rating": 8.3,
  "status": "available",            // available | processing | banned | repairing
"intro_timings": { "start": 90, "end": 150, "votes": 5 }, // Timestamp in seconds

  // 🖼️ VISUALS
  "visuals": {
    "poster": "AgADxxxx",           // Telegram File ID
    "backdrop": "AgADxxxx",
    "screenshots": ["AgAD...1", "AgAD...2"]
  },

  // 🎞️ VIDEO BUCKETS
  "files": [
    {
      "quality": "2160p",
      "label": "4K HDR",
      "size_human": "14.2 GB",
      "telegram_id": "BAACAg...",
      "file_hash": "nginx_cache_key", // VIP Source (ShadowStream)

// ➕ CRITICAL: RAW MTPROTO KEYS (Required for Go Engine/gotgproto)
      "tg_raw": {
          "media_id": 123456789,
          "access_hash": -987654321,
          "file_reference": "060000..." 
      },

      // Public Embeds (Free Tier)
      "embeds": [
        { "host": "VidHide", "url": "https://vidhide.com/embed/xyz", "priority": 1 },
        { "host": "StreamTape", "url": "https://streamtape.com/e/xyz", "priority": 2 }
      ],
      
      "backup_url": "https://pixeldrain.com/u/xyz" // Download Mirror
      
      // Critical for Soft Subtitles
      "subtitles": [
        { "lang": "eng", "index": 3 }, // Stream #0:3
        { "lang": "spa", "index": 4 }
      ],

      // ➕ NEW: The Archive Page Data
      "downloads": [
        { 
          "host": "Gofile", 
          "url": "https://gofile.io/d/xyz", 
          "icon": "icon_gofile.png",
          "status": "active" 
        },
        { 
          "host": "PixelDrain", 
          "url": "https://pixeldrain.com/u/xyz", 
          "icon": "icon_pixeldrain.png", 
          "status": "active" 
        },
        { 
          "host": "HubCloud", 
          "url": "https://hubcloud.club/...", 
          "icon": "icon_hubcloud.png",
          "status": "dead" // Bot checks this
        }
      ]
    }
  ]
}
```

### B. Series Entity
```json
{
  "_id": "tmdb_1399",
  "media_type": "series",
  "title": "Game of Thrones",
  "total_seasons": 8,
  
  // 📦 SEASON PACKS
  "season_packs": [
    { "season": 1, "zip_file_id": "BAACAg...", "size": "25 GB" }
  ],

  // 📺 EPISODES
  "seasons": {
    "1": [
      { "episode": 1, "title": "Winter Is Coming", "file_id": "BAACAg...", "quality": "1080p" }
    ]
  }
}
```

### C. Manga/Book Entity (ReadVault)
```json
{
  "_id": "manga_solo_leveling",
  "media_type": "manga",
  "content_rating": "safe",        // safe | 18+
  "chapter_count": 179,

  // 📖 CHAPTERS
  "chapters": [
    {
      "chap": 1.0,
      "title": "I'm Used to It",
      "storage_id": "-100xxxx",    // Log Channel ID
      "pages": ["file_id_p1", "file_id_p2"]
    }
  ]
}
```

---

## 👥 Collection: `users` (Identity & Progress)
```json
{
  "_id": 123456789,                // Telegram ID OR "guest_hash"
  "type": "telegram",              // telegram | guest
  "role": "free",                  // free | premium | admin
  
  // 🛡️ SECURITY & ANTI-SHARE
  "security": {
    "auth_token_secret": "salt_xyz",
    "active_sessions": 1,          // Redis counter sync
    "bound_device": {
       "hash": "useragent_hash",
       "locked_at": ISODate(...) 
    }
  },

  // 🍿 WATCH/READ HISTORY
  "history": {
    "tmdb_299534": { "timestamp": 3405, "updated_at": ISODate(...) }, // Video
    "manga_solo": { "last_chap": 55, "last_page": 3 }                 // Manga
  },

  // 🤝 REFERRAL
  "referral": { "code": "john_x", "invited_count": 5, "invited_by": 987 }
}
```

---

## 🏗️ Collection: `workers` (The Swarm)
```json
{
  "_id": "worker_01",
  "api_id": 123456,
  "status": "active",             // active | flood_wait | dead
  "current_task": "leeching_avengers",
  "flood_wait_until": ISODate(...) 
}
```

---

## 🚑 Collection: `reports` (The Medic)
```json
{
  "_id": "rep_1",
  "target_id": "tmdb_299534",
  "issue": "dead_link",           // dead_link | wrong_audio | missing_pages
  "status": "pending"             // pending | fixed
}
```

---

## 💬 Collection: `comments` (Ghost System)
*Self-hosted community interaction. Decoupled from Telegram to preserve privacy.*
```json
{
  "_id": "comment_x8s9d",
  "target_id": "tmdb_299534",        // ID of Movie, Series, or Manga Chapter
  "user_id": 123456,                 // Links to Users Collection (Guest Cookie or Telegram ID)
  "nickname": "ShadowReader_99",     // Auto-generated if Guest
  "avatar_seed": "x8s9d",            // Seed for DiceBear deterministic avatars
  
  "body": "That ending was insane! >!Spoiler Text!<",
  "is_spoiler": true,                // If true, blurred until clicked
  
  "timestamp": 450,                  // (Optional) Video second for "Timeline Comments"
  "likes": 12,
  "created_at": ISODate(...),
  
  "moderation_status": "active"      // active | flagged | deleted
}
```
---

## 🏢 Collection: `tenants` (B2B / Franchise)
*Stores configuration for external sites using our platform.*
```json
{
  "_id": "tenant_x99",
  "domain": "anime-hub.com",
  "owner_email": "client@gmail.com",
  "plan": "rev_share",                // rev_share | fixed_fee
  "status": "active",                 // active | suspended | past_due
  
  // 🔌 RESOURCES & ADD-ONS
  "addons": {
    "android_app": { "active": true, "apk_url": "..." },
    "dmca_shield": { "active": false },
    "capacity": { "tier": 1 }
  },
  
  // 📅 BILLING CYCLE
  "subscription": {
    "start_date": ISODate("..."),
    "next_bill_date": ISODate("..."),
    "payment_method": "crypto"
  },

  // 📊 CACHED STATS (For fast Admin Dashboard)
  "stats": {
    "monthly_visitors": 45000,
    "bandwidth_used_gb": 120,
    "revenue_generated": 150.50
  }
}
```
---

## ⚡ Indexing Commands (Run these in Mongo Compass)
1.  **Unified Search:** `db.library.createIndex({ title: "text", author: "text" })`
2.  **User Lookup:** `db.users.createIndex({ "referral.code": 1 })`
3.  **Content Filter:** `db.library.createIndex({ media_type: 1, content_rating: 1 })`
4. **Instant lookups for slugs**
`db.library.createIndex({ "short_id": 1 }, { unique: true })`
```
