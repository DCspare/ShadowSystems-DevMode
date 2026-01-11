Here are the specific `requirements.txt` files for each Python component in your Monorepo.

These versions are selected for stability on **Python 3.10** (Oracle/Debian) and ensure the specific libraries (`pyrogram`, `fastapi`, `motor`) play nicely together.

---

### 1. `apps/manager/requirements.txt`
**Role:** API Server + Bot Logic + Database Mgmt.

```text
# --- Web Framework ---
fastapi==0.109.2
uvicorn==0.27.1         # Pure Uvicorn (Safer for Pyrogram integration)
python-multipart==0.0.9 # For uploading files/forms

# --- Telegram Core ---
pyrogram==2.0.106       # Stable version
tgcrypto==1.2.5         # Critical for encryption speed on ARM64

# --- Database & Cache ---
motor==3.3.2            # MongoDB Async Driver
dnspython==2.6.1        # Required for Mongo Atlas DNS resolution
redis==5.0.1            # Async Redis client

# --- Auth & Security ---
python-jose[cryptography]==3.3.0  # For generating/verifying Magic Link JWTs
passlib[bcrypt]==1.7.4            # For hashing admin secrets

# --- Utilities ---
aiohttp==3.9.3          # For external API calls (TMDB, Ad Shorteners)
python-dotenv==1.0.1    # Managing .env variables
prometheus-client==0.20.0 # For the Admin Dashboard metrics

# --- Metadata Hoarding (Scraping TMDB/MAL without getting blocked) ---
fake-useragent==1.4.0   # To spoof headers when scraping metadata
pydantic==2.6.1         # For defining strict schemas (FastAPI data validation)
email-validator==2.1.0  # For validating User Signups (Guest -> Magic Link)
```

---

### 2. `apps/worker-video/requirements.txt`
**Role:** The "Heavy Lifter" (StreamVault Video Worker).

```text
# --- Telegram Core ---
pyrogram==2.0.106
tgcrypto==1.2.5

# --- Networking ---
pysocks==1.7.1          # CRITICAL: Enables SOCKS5 Proxy support for bypass
aiohttp==3.9.3          # For connecting to Mirror APIs (StreamWish/PixelDrain)

# --- Database ---
motor==3.3.2
dnspython==2.6.1

# --- File Operations ---
aiofiles==23.2.1        # Async file I/O (essential for high-speed disk writes)
python-dotenv==1.0.1

# --- Smart Renaming Engine & Metadata Extraction ---
PTN==2.2.3              # CRITICAL: For parsing/renaming torrent file names
hachoir==3.1.2          # CRITICAL: For Pyrogram video metadata extraction
tenacity==8.2.3         # For robust retry logic if a Mirror Upload fails
mutagen==1.47.0         # For embedding Album Art and ID3 tags into MP3s

# --- Download Engines ---
yt-dlp==2023.11.16      # The Gold Standard for scraping video from ANY site
aria2p==0.11.0          # Python wrapper to control the Aria2 system binary
beautifulsoup4==4.12.3  # For parsing raw HTML when yt-dlp fails
requests==2.31.0        # Fallback HTTP library
```

---

### 3. `apps/worker-manga/requirements.txt`
**Role:** The "Scraper" (ReadVault Manga/Book Worker).

```text
# --- Telegram Core ---
pyrogram==2.0.106
tgcrypto==1.2.5

# --- Scraper Tools ---
gallery-dl==1.26.6      # The Manga Image Scraper engine
pikepdf==8.13.0         # For modifying PDF Metadata (Books) on the fly

# --- Database ---
motor==3.3.2
dnspython==2.6.1

# --- Utils ---
aiohttp==3.9.3
python-dotenv==1.0.1
pillow==10.2.0          # Image processing library (Needed for "Data Saver" conversion)

# --- PDF Metadata Injection (StreamVault Branding) ---
EbookLib==0.18          # For parsing/modifying EPUB files (BookVault)
bs4==0.0.1              # BeautifulSoup: Fallback if Gallery-DL fails for a specific site
```

---

**Frontend Lib:** `npm install hls.js` (Required for ArtPlayer streaming compatibility).

### ⚠️ Technical Note for the AI
When using `gallery-dl`, it is often updated more frequently than PyPI.
If `pip install gallery-dl` fails to grab a supported site, you might need to instruct the AI/Terminal to install from the repo directly:
`pip install https://github.com/mikf/gallery-dl/archive/master.tar.gz`

But for now, the standard requirements above are correct for the setup.
