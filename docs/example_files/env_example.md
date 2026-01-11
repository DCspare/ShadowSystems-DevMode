 **Reference Usage:**
> **Env:** Copy contents of `env_example.md` to `.env` in the root folder.
> *Note: Do **NOT** commit your real `.env` file to GitHub. Add it to `.gitignore` first before committing files.*

 ---------------------------------------------------
### 🌍 PROJECT: Shadow Systems (V2 + ReadVault Lite)
 ---------------------------------------------------

### ===================================
### ⚠️ SETUP GUIDE: PRODUCTION VS DEVELOPMENT (POTATO MODE)
### ===================================
#
### COPY this file to .env and uncomment/edit the lines below based on your environment.
#
## 🟢 MODE A: ORACLE VPS / LOCAL DOCKER DESKTOP (PRODUCTION SIMULATION)
### Keep defaults below. 
### -> `MONGO_URL=mongodb://db-mongo:27017/shadow_db`
### -> `REDIS_URL=redis://db-redis:6379/0`
#
## 🟠 MODE B: CLOUD IDE (CODESPACES / PROJECT IDX)
## Change these 4 variables to prevent crashes:
#
### 1. `MODE=DEV`
### 2. `DOMAIN_NAME=your-tunnel-id.trycloudflare.com` (Get this from Cloudflared logs)
### 3. `MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/shadow_dev` (Use Atlas Free Tier)
### 4. `REDIS_URL=rediss://default:pass@url.upstash.io:6379` (Use Upstash Free Tier - Note 'rediss' for SSL)
#
### ==================================

### --- ENVIRONMENT SETUP ---
```
MODE=PROD                  # DEV or PROD
LOG_LEVEL=INFO             # DEBUG for verbose logs
DOMAIN_NAME=shadow-systems.xyz

# File Branding
FILE_BRANDING_TAG=[ShadowSystem]  # Will be appended to every uploaded file
AUTO_RENAME_VIDEOS=True           # Enable PTN parsing
```

### --- TELEGRAM SECRETS (Manager Identity) ---
```
# Used by Manager Bot for Auth and Metadata
TG_API_ID=1234567
TG_API_HASH=your_api_hash
TG_BOT_TOKEN=123:ABC_Def...
```

### --- CHANNEL MAPPING (Critical) ---
```
# Where movies/files are stored (The "Cloud Drive")
# Primary Storage
TG_LOG_CHANNEL_ID=-100xxxxxxxxxx 
# Secret Redundancy Storage (Forward Copy)
TG_BACKUP_CHANNEL_ID=-100xxxxxxxxxx
# Where Audio files (OST/Music) are uploaded
TG_MUSIC_CHANNEL_ID=-100xxxxxxxxxx

# Where Updates/Cards are posted
TG_UPDATE_CHANNEL_ID=-100xxxxxxxxxx

# Where "Crowdsourced" User uploads go for approval
TG_DUMP_CHANNEL_ID=-100xxxxxxxxxx

# Your Personal Telegram User ID (Super Admin)
TG_OWNER_ID=123456789
```

### --- DATABASE CLUSTER ---
```
# Internal Docker DNS: 'db-mongo' and 'db-redis'
MONGO_URL=mongodb://db-mongo:27017/shadow_db
REDIS_URL=redis://db-redis:6379/0
```

### --- SECURITY & AUTH ---
```
JWT_SECRET=generate_random_long_string_here_x99
ADMIN_SECRET=master_password_for_emergency_login
HASH_SALT=another_random_string_for_device_locks
SECURE_LINK_SECRET=random_complex_string_match_this_in_nginx_conf
```

### --- WORKER HIVE CONFIG ---
```
# Directory where .session files are loaded from
SESSION_FOLDER=/app/sessions/workers
# Max concurrent leeches per worker (prevents crash)
WORKER_CONCURRENCY=3

GENERATE_SAMPLES=True     # Generate 30s preview clip? (Uses CPU)
```

### --- 3RD PARTY APIS (Metadata) ---
```
TMDB_API_KEY=your_tmdb_key
MAL_CLIENT_ID=your_myanimelist_id # For Manga Metadata
```

### --- MONETIZATION (Ad Network Keys) ---
```
SHORTENER_API_URL=https://gplinks.in/api
SHORTENER_API_TOKEN=your_token
ADSTERRA_PID=your_placement_id
```

### --- BACKUP MIRRORS (Upload Keys) ---
```
STREAMWISH_KEY=your_key
PIXELDRAIN_KEY=your_key
ABYSS_KEY=your_key

# --- PUBLIC EMBED HOSTS (Free Tier Streaming) ---
# Used for Remote Uploads (Daisy Chaining)
VIDHIDE_API_KEY=your_key
STREAMTAPE_API_LOGIN=your_login
STREAMTAPE_API_KEY=your_key
FILELIONS_API_KEY=your_key
```

### --- READVAULT (Manga) SPECIFIC ---
```
# Cookie file for Gallery-DL to access premium sites
GALLERY_DL_COOKIES=/app/cookies.txt
**`COOKIES_FILE_PATH=/app/cookies.txt`** (Make this variable shared for both Workers).
```
