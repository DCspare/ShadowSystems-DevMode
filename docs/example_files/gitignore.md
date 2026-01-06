> Refrence Use<br>
> **Action:** Create a file named `.gitignore` (no extension) in your **Project Root** and paste this content inside immediately. This "locks" your git repo before you start building.

```gitignore
# ------------------------------------------------
# SHADOW SYSTEMS: GLOBAL GITIGNORE
# ------------------------------------------------

# --- 🔒 SECRETS & KEYS (NEVER COMMIT THESE) ---
.env
.env.production
.env.local
.env.*.local

# --- 🐳 DATA VOLUMES (PERSISTENT STORAGE) ---
# Ignores the database files and video cache
data/
data/mongo/
data/redis/
data/cache/
data/sessions/

# --- 🐝 TELEGRAM SESSIONS ---
# Ignores authentication files for workers
config/workers/*.session
config/workers/*.session-journal
apps/worker-video/*.session
apps/worker-manga/*.session
apps/manager/*.session

# --- 🐍 PYTHON (Backend) ---
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
prof/

# --- 🕸️ NEXT.JS (Frontend) ---
apps/web/node_modules/
apps/web/.next/
apps/web/out/
apps/web/build/
apps/web/dist/
apps/web/.DS_Store
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# --- 🐹 GOLANG (Stream Engine) ---
apps/stream-engine/stream-engine
apps/stream-engine/*.exe
apps/stream-engine/*.test
apps/stream-engine/*.out

# --- 💻 IDE SETTINGS ---
.vscode/
.idea/
*.swp
*.swo

# --- 📦 MISC ---
.coverage
htmlcov/
*.zip
*.tar.gz
temp/
tmp/

# --- 🍪 BROWSER COOKIES (CRITICAL SECURITY) ---
# Prevents uploading Gallery-DL / Authentication cookies
cookies.txt
cookies.json
*cookie*.txt
*cookie*.json
```
