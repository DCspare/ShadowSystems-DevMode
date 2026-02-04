## 🛠 The Hurdle Log: Challenges & Resolutions
*The **"Shadow Survivor's Log"**. It documents every technical roadblock we encountered during Phase 1 & 2 in the Google Project IDX environment and the exact "Shadow Protocol" fixes we applied.*

#### 1. The Nix "Sudo" Conflict
*   **The Error:** `sudo: /usr/bin/sudo must be owned by uid 0 and have the setuid bit set`.
*   **Description:** Google IDX runs on Nix, which uses an unprivileged environment. Traditional `sudo` commands for permission changes fail because the user doesn't have root-level filesystem modification rights inside the Nix store.
*   **The Fix:** Use the built-in **UID 1000** (standard for IDX) and avoid `sudo` for directory operations. We handled this by adding system service declarations in `.idx/dev.nix`.
*   **Command:** 
    ```bash
    # Instead of sudo, use Nix user identity
    chown -R $(id -u):$(id -g) apps/ config/ data/
    ```

#### 2. The Silent Docker Daemon
*   **The Error:** `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`.
*   **Description:** By default, the Docker service isn't "hot" in a new IDX workspace. Even with the package installed, the socket connection isn't bridged.
*   **The Fix:** Explicitly enabled `services.docker.enable = true` in `.idx/dev.nix` and performed an environment **Rebuild**. This creates the persistent socket bridge.
*   **Protocol:** Always "Rebuild Environment" after editing `.idx/dev.nix`.

#### 3. The Pymongo/Motor Version Collision
*   **The Error:** `ImportError: cannot import name '_QUERY_OPTIONS' from 'pymongo.cursor'`.
*   **Description:** A breaking change in the `pymongo` driver (v4.7+) removed internal options that the `motor` (async driver) 3.3.2 library relied upon.
*   **The Fix:** Strict version pinning in `requirements.txt`.
*   **Solution:** 
    ```text
    motor==3.3.2
    pymongo==4.6.3 # Locked to prevent internal breakage
    ```

#### 4. Atlas Connection "Anonymous" DB Error
*   **The Error:** `pymongo.errors.ConfigurationError: No default database name defined or provided`.
*   **Description:** MongoDB Atlas connection strings often omit the database name at the end of the URL. The standard `get_default_database()` method crashes if the path doesn't end with a `/dbname`.
*   **The Fix:** Patched `database.py` and `worker.py` with a manual fallback check.
*   **Logic:** 
    ```python
    try:
        self.db = mongo_client.get_default_database()
    except Exception:
        self.db = mongo_client["shadow_systems"] # Hardcoded fallback
    ```

#### 5. The SQLite "Readonly" Session Error
*   **The Error:** `TELEGRAM CRITICAL: attempt to write a readonly database` (or `unable to open database file`).
*   **Description:** Pyrogram uses SQLite to manage sessions. When mounted inside a Docker container, it needs to create temporary "journal" files. If the parent folder is not globally writable, the OS rejects the creation of the lock file.
*   **The Fix:** Used absolute paths for `workdir` and applied a recursive `777` chmod on the `data/sessions` host folder.
*   **Command:** 
    ```bash
    chmod -R 777 data/sessions
    ```

#### 6. Media Parser Library Collision (PTN)
*   **The Error:** `Could not find a version that satisfies the requirement PTN>=2.3.0` and Python 3.10 incompatibility.
*   **Description:** The Torrent Name Parser (`ptn`) library had a naming collision on PyPI with another package. Furthermore, modern versions required Python 3.12, while we were using 3.10.
*   **The Fix:** Upgraded Worker base image to **Python 3.12-slim** and pulled the media parser directly from the official source GitHub repository.
*   **Requirement Solution:** 
    ```text
    git+https://github.com/divijbindlish/parse-torrent-name.git
    ```

#### 7. IDX "Welcome to Nginx" 8080 Redirect
*   **The Error:** Seeing the standard Nginx landing page instead of API JSON on the Public URL.
*   **Description:** Browser caching and an over-generalized `location /` block in `nginx.conf` caused the Gateway to serve static files instead of proxying traffic to the Manager Brain.
*   **The Fix:** Refined `nginx.conf` with a specific `/api/` rewrite rule and removed the root landing page, allowing FastAPI to handle root requests directly via the proxy.
*   **Access Pattern:** Use `https://your-url.dev/api/library/list`.

Upon reviewing our detailed interaction logs from the start, there are **three specific hurdles** we encountered that were missing from the previous log. I have generated them here for your `README.md` or `DEBUG_LOG.md`.

#### 8. The "Root package.json" Preview Crash
*   **The Error:** `Error: ENOENT: no such file or directory, open '/home/user/shadow-systems/package.json'`.
*   **Description:** Google Project IDX’s "Web Preview" logic defaults to looking for a Node.js `package.json` in the root folder to start a development server. Since Shadow Systems is a monorepo and our frontend is inside `apps/web/`, IDX failed to launch.
*   **The Fix:** Updated `.idx/dev.nix` to change the preview command to `tail -f /dev/null`. This satisfies IDX's need for a running command while allowing our **Nginx Gateway (Port 8080)** to handle the actual traffic via Docker.

#### 9. Python Package Discovery Failure
*   **The Error:** `ImportError: cannot import name 'bot_manager' from 'services.bot_manager'`.
*   **Description:** Python does not automatically treat folders as "packages" unless they contain an initialization file. This caused the Manager Brain to fail during boot as it couldn't see our custom services.
*   **The Fix:** Manually initialized the package structure.
*   **Command:** 
    ```bash
    touch apps/manager/core/__init__.py apps/manager/services/__init__.py
    ```

#### 10. The "DCNone" / Handshake Shutdown Loop
*   **The Error:** `ConnectionError: Client is already terminated` followed by `KeyError: 0`.
*   **Description:** During the first Telegram handshake in a new container, Pyrogram often cycles through different Data Centers (DCs). If the app is shut down while this handshake is happening (due to a restart or an error), it creates a corrupted local SQLite session file.
*   **The Fix:** Wrapped the `bot.stop()` logic in a `try/except` block and added a manual check for `app.is_connected`.
*   **Protocol:** Before restarting a failed bot, always wipe the specific `.session` file in `data/sessions/` to ensure a clean handshake.

#### 🧱 Hurdle #11: Group Visibility & Peer Resolution
*   **The Error:** `ValueError: Peer id invalid` or `KeyError: ID not found`.
*   **Description:** When using **Telegram Supergroups** (ID starting with `-100...`) instead of Channels, MTProto clients (Pyrogram) sometimes fail to resolve the peer if the bot has never "interacted" with that group. Adding the bot as Admin is the first step, but it may still be "blind" to the ID until the local `sqlite` session caches the peer information.
*   **The Fix:** Force the bot to resolve the peer by attempting a broad `get_chat` call, and ensuring the group's "Chat History" is visible to new members/admins. 
*   **Protocol:** In some cases, manually sending a single message to the group (e.g., `/start`) and then restarting the container forces the SQLite database to sync the group's metadata.

#### 🧱 Hurdle #12: The Docker "Mount Path" Trap
- **The Error:** `Metadata probe failed: Unable to open file /apps/worker-video/... [Errno 2] No such file or directory`.
- **Description:** On the host, the file lives in `apps/worker-video/`. Inside the Docker container, that directory is mounted as `/app/`. Code running inside the worker cannot see the "Host Path."
- **The Fix:** Explicitly used the absolute container path `/app/` for logic, and migrated the media ingestion logic to utilize the globally writable `/tmp/` directory for high-speed, transient processing.

#### 🧱 Hurdle #13: The SQLite "Session Lock" Conflict
- **The Error:** `unable to open database file`.
- **Description:** Only one process (the background worker) can hold the SQLite database lock for a specific `.session` file. Trying to run a standalone "Test Script" with the same session name results in an immediate crash.
- **The Fix:** Implemented a **"Temporary Runner" pattern** using `docker compose run` and established a **Redis Task Queue** (`queue:leech`). This allows the Manager to talk to the Worker safely via Redis messages without needing to manually run Python scripts or clash over session locks.

#### 🧱 Hurdle #14: The Cloud-Workspace "Operation Not Permitted" Lockout
- **The Error:** `chmod: changing permissions... Operation not permitted`.
- **Description:** Google IDX restricts `sudo` in the Nix shell. When Docker (running as root) creates files like `.session-journal`, the terminal user loses permission to modify or delete them.
- **The Fix:** **The "Shadow Bypass" (Docker Privilege Escalation).** Used an Alpine Linux container to mount the host project and run root-level permission resets.
- **Protocol Command:**
  ```bash
  docker run --rm -v "$(pwd):/work" alpine sh -c "chmod -R 777 /work/data /work/apps"
  ```

#### 🧱 Hurdle #15: The Nginx Environment Variable Silent Failure
- **The Error:** Nginx returning 403 Forbidden even with correct URL format.
- **Description:** Nginx's native configuration cannot read the `.env` file directly. When we moved from hardcoding to variables, Nginx saw an empty string for the secret.
- **The Fix:** Migrated to the `nginx:alpine` **Template pattern**. Docker-compose now injects the `${SECURE_LINK_SECRET}` into a `.template` file which Nginx converts into a final configuration at runtime.

#### 🧱 Hurdle #16: Nested Proxy IP Blindness
- **The Error:** `{"status": "denied", "ip_seen": "172.20.0.1"}`.
- **Description:** Manager signed links using the internal Docker container IP of the Nginx gateway, while Nginx was verifying links using the Bridge IP of the host.
- **The Fix:** Configured "Proxy Trust" in the Python Brain. The router now prioritizes the `X-Real-IP` header, ensuring both the Brain and the Bouncer agree on the requester's identity.

#### 🧱 Hurdle #17: Docker Compose "Mapping Error"
- **The Error:** `services.services must be a mapping`.
- **Description:** A syntax duplication occurred where the key `services:` was accidentally nested twice during a configuration update.
- **The Fix:** Hard-reset of the `docker-compose.dev.yml` structure, ensuring the flat-hierarchy of Monorepo services.

#### 🧱 Hurdle #18: The Go Binary Cold-Start
- **The Error:** Delayed response on the first stream request in IDX.
- **Description:** The Go Dockerfile utilizes a multi-stage build. During the first `up`, Go downloads dependencies and compiles. 
- **The Fix:** Implemented a non-blocking `health` probe and standard Docker `depends_on` logic to ensure the Brain waits for the Muscle to be fully compiled before accepting traffic.

#### 🧱 Hurdle #19: Docker EOF "Backslash" Injection
- **The Error:** `strconv.Atoi: parsing "\\11603806": invalid syntax`.
- **Description:** Using a standard `cat << EOF` in the terminal caused the shell to attempt variable expansion or escape processing, resulting in literal backslashes being written into the `docker-compose` file.
- **The Fix:** Migrated to the **Quoted EOF pattern (`cat << 'EOF'`)**, which forces the terminal to treat all characters as raw text, ensuring the Docker engine receives clean environment variables.

#### 🧱 Hurdle #20: MTProto Connection Instability (DC Cycle)
- **The Error:** Intermittent `DC_ID_INVALID` or socket drops during initialization.
- **Description:** Cloud IDE networks (Google IDX) often have fluctuating latency during the initial handshake with Telegram’s global data centers (DC2 to DC5).
- **The Fix:** Implemented a **"Stabilizer Delay"** in the Go routine, allowing the MTProto network task to fully bridge before attempting the `Auth().Bot()` sequence.

#### 🧱 Hurdle #21: The "Peer ID Invalid" Loop
*   **Problem:** New Telegram sessions cannot "Find" a channel ID just by the integer (e.g., `-100xx`). They need the Access Hash, which is only cached after an interaction.
*   **Fix:**
    *   `get_dialogs` sweep (Failed - Bots can't call this).
        *   **Solution:** Added manual `/health` command. Admin sends this in the log channel once per restart. The bot receives the message update -> Pyrogram caches the Peer hash -> Uploads work.

#### 🧱 Hurdle #22: Dependency Confusion (`apt` vs `pip`)
- **Problem:** Docker build failed because we tried to install `yt-dlp` via `apt-get` (Linux), but it is a Python package.
- **Fix:** Removed `yt-dlp` from Dockerfile system installs and pinned it strictly in `requirements.txt`.

#### 🧱 Hurdle #23: Docker Caching Conflicts
        *   **Problem:** After adding `aria2` to Dockerfile, the container still crashed with "Command not found".
        *   **Cause:** Docker reused an old cached layer that didn't have the binary.
        *   **Fix:** Forced rebuild: `docker compose build --no-cache worker-video`.

#### 🧱 Hurdle #24: Aria2 "Error 16" (Cloud Filesystem)
*   **Problem:** `Download aborted` instantly on Cloud IDEs due to `fallocate` failures on virtual filesystems.
*   **Fix:**
    1.  Configured Aria2 with `--file-allocation=none`.
    2.  Implemented **"Hybrid Downloader"**: Falls back to `yt-dlp` native sockets if Aria2 connection drops.
    3.  Implemented **Entrypoint Script**: Runs `chmod 777` as root on container startup to fix volume mount permissions.

#### 🧱 Hurdle #25: The Bash Variable "Blanking"
*   **Problem:** Python logic was deleted when creating files via terminal because `$push` and `$set` were interpreted as bash variables (empty).
*   **Fix:** Switched to **Quoted EOF** pattern (`cat <<'EOF'`) to treat the entire code block as a string literal.

#### 🧱 Hurdle #26: The "Blind Bot" (Peer Resolution)
*   **Problem:** The Go Engine crashed with `CHANNEL_INVALID` despite having the correct ID.
*   **Description:** Telegram APIs do not allow access to a peer via ID alone; an `AccessHash` is required. The bot had no memory of the channel.
*   **Fix:** Switched to **`gotgproto`** with **SQLite PeerStorage**. This allows the bot to "Learn" the hash from incoming updates (like a `/health` command) and store it permanently on disk, removing the need for constant handshakes.

#### 🧱 Hurdle #27: The Compiler Logic Trap
*   **Problem:** Go Compiler refused to build `downloader.go` due to unused imports when context logic was simplified.
*   **Fix:** Implemented defensive coding pattern `_ = context.Background` to force compiler compliance while maintaining strict context propagation for request cancellation.

#### 🧱 Hurdle #28: The "Infinite Stream" (No Scrubbing)
*   **Problem:** Video played but had no timeline bar/duration, effectively behaving like a live stream.
*   **Description:** The HTTP response lacked the `Content-Length` header because Telegram streams don't provide it automatically during the initial packet.
*   **Fix:** Updated the Resolver logic to extract `Document.Size` from the metadata packet and injected standard HTTP `Content-Length` and `Content-Range` headers before opening the data stream.

#### 🧱 Hurdle #29: MTProto Alignment (Offset Invalid)
*   **Problem:** Seeking to random timestamps caused `RPC_ERROR: OFFSET_INVALID`.
*   **Description:** Telegram requires download offsets to be aligned to specific block sizes (usually 1MB or 4KB). Browsers request random byte bytes (e.g., `bytes=52352-`).
*   **Fix:** Implemented **"Elastic Buffering"**. The Go engine calculates the nearest downward-aligned 1MB chunk, fetches it from Telegram, and locally **trims** the unneeded bytes from the start of the buffer before piping to the client.

#### 🧱 Hurdle #30: The Identity Wall (400 Bad Request)
*   **Problem:** Python Manager could find files, but Go Engine (using a different Bot Token) got `FILE_REFERENCE_EXPIRED` errors accessing them.
*   **Description:** Telegram Access Hashes and File References are often scoped to the Session/User ID. Tokens cannot always be shared across different identities.
*   **Fix:** **Identity Cloning**. Configured the Go Engine to ingest the **Pyrogram User Session String** from `.env`. This allows the Streamer to connect as the exact same "User" as the Leecher, guaranteeing 100% permission compatibility.

#### 🧱 Hurdle #31: Python Scope Shadows
*   **The Error:** `name 'video' is not defined` crash in Media Processor.
*   **Description:** Variable definitions inside `try/except` blocks in Python are not scoped globally if the block fails early or loops don't trigger.
*   **The Fix:** Refactored `processor.py` to initialize all default values (0, empty lists) *before* entering the try/logic block.

#### 🧱 Hurdle #32: Pyrogram Album Captions
*   **The Error:** Uploading screenshots as an Album caused the Caption to disappear.
*   **Description:** Telegram Media Groups only display the caption attached to the *first* item in the array. If logic conditionally added items (like skipping sample video), the caption index was off.
*   **The Fix:** Updated `leech.py` to force-attach the caption to `media_group[0]` immediately before sending, regardless of media type.

#### 🧱 Hurdle #33: MongoDB Upsert Conflict
*   **The Error:** `update only works with $ operators`.
*   **Description:** Using `upsert=True` fails if the document skeleton definition is mixed inside the `$push` logic dynamically without strict separation.
*   **The Fix:** Split the DB Write logic into strict branches: `find_one` -> If exists `update_one` ($push) -> Else `insert_one` (Full Skeleton).

#### 🧱 Hurdle #34: Python Module "Sibling" Imports in Docker
*   **The Error:** `ModuleNotFoundError: No module named 'apps'` when importing shared schemas.
*   **Description:** Python treats imports relative to the working directory. In Docker, our root is `/app`. Tries to import `apps.shared` failed because the folder structure inside container didn't match host exactly.
*   **The Fix:** Implemented `sys.path.append("/app/shared")` and strict volume mounting in Docker Compose (`./apps/shared:/app/shared`) to make the kernel accessible to all containers.

#### 🧱 Hurdle #35: The Button 400 Invalid URL
*   **The Error:** `BUTTON_URL_INVALID` causing worker crash.
*   **Description:** Telegram API strictly rejects Inline Buttons if the URL starts with `http://` or `localhost`. This crashed the bot during local testing tunnels without SSL.
*   **The Fix:** Added strict validation in `formatter.py`: If `DOMAIN_NAME` does not start with `https://`, the bot suppresses the generation of "Watch Online" buttons to prevent crashes in Dev Mode.

#### 🧱 Hurdle #36: The "Variables from Thin Air" Trap
*   **The Error:** `UnboundLocalError: local variable 'video' referenced before assignment`.
*   **Description:** In the FFprobe parser, we defined variables inside a `try` block or a loop. If the loop didn't run (empty streams), the variable remained undefined, crashing the cleanup logic.
*   **The Fix:** Adopted the **"Defaults First"** pattern. All return dictionaries are initialized with safe default values (0, empty list) *before* processing begins, ensuring `leech.py` never receives `NoneType`.

#### 🧱 Hurdle #37: Pydantic "Missing Field" Crash
*   **The Error:** `pydantic.error_wrappers.ValidationError` on app startup.
*   **Description:** Switching to strict `settings.py` caused the app to crash because `.env` was missing new keys (like `API_SECRET_KEY`) that were marked as required strings.
*   **The Fix:** Updated `SettingsConfigDict` to allow `extra="ignore"` and provided sensible default values (`= None` or `"unsafe_default"`) for optional keys to prevent boot loops during dev setup.

#### 🧱 Hurdle #38: The Variable "Name Shadow"
*   **The Error:** `UnboundLocalError: local variable 'video' referenced before assignment`.
*   **Description:** Python's scoping rules inside `try/except` blocks caused variables defined only in the happy path to be undefined during the exception handler logic.
*   **The Fix:** Adopted a "Defense-First" initialization pattern where all return variables (width, height, duration) are set to `0` or `None` at the very top of the function, ensuring they exist regardless of execution flow.

#### 🧱 Hurdle #39: MongoDB Operator Injection
*   **The Error:** `update only works with $ operators`.
*   **Description:** Bash Heredocs (`cat <<EOF`) attempted to expand `$push` and `$set` as shell variables, resulting in empty strings being written to the Python file.
*   **The Fix:** Switched to **Quoted Heredocs** (`cat <<'EOF'`) to treat the input as a raw string, preserving the MongoDB operator syntax inside the container.

#### 🧱 Hurdle #40: The Internal Header Bridge
- **The Error:** `HTTP 400 Bad Request` or `500 Internal Error` when calling subtitles.
- **Description:** The Manager API (Python) tried to call the Go Stream Engine directly. However, the Go Engine requires `X-Location-Msg-ID` headers to find the Telegram file. Since the browser doesn't send these, the request failed.
- **The Fix:** Implemented a "Smart Resolver" in `library.py`. The Manager now fetches the location data from MongoDB first, then injects those headers into the `subprocess.Popen` FFmpeg command via the `-headers` flag.

#### 🧱 Hurdle #41: FastAPI Type-Strictness (Parsing Fail)
- **The Error:** `HTTP 422 Unprocessable Entity`.
- **Description:** A request to `/subtitle/{file_id}/index3.vtt` failed because the route expected an `int` for the index. The string "index3" could not be cast to an integer.
- **The Fix:** Corrected the frontend/CURL calling pattern to pass only the integer (e.g., `/subtitle/{file_id}/3.vtt`). Strictly enforced integer type-hinting in FastAPI to prevent command injection.

#### 🧱 Hurdle #42: The Peer Resolution Wall
- **The Error:** `Peer id invalid` or `400 BOT_METHOD_INVALID`.
- **Description:** Fresh Docker sessions lacked the "Access Hash" for private log channels. Bots are restricted from using `GetDialogs` to sync these hashes.
- **The Fix:** Implemented the "Silent Pulse" protocol. The worker now attempts a sequence of `send_chat_action`, `get_chat_history`, and `get_chat_member` on startup. This forces Telegram to push the peer data to the bot, caching the hash in the local session database autonomously.

#### 🧱 Hurdle #43: The "NoneType" Socket Interruption
- **The Error:** `AttributeError: 'NoneType' object has no attribute 'write'` or `'id'`.
- **Description:** Forcefully raising exceptions inside Pyrogram progress callbacks interrupted the MTProto transport layer, leading to crashes during cleanup or indexing.
- **The Fix:** Adopted the official `StopTransmission` signal for graceful socket closure. Added "Late-Binding" scope checks using `locals().get()` and `if video_msg is None` guards to ensure the worker skips indexing and proceeds to cleanup without crashing if a task is aborted mid-flight.

#### 🧱 Hurdle #44: The Async Heartbeat Race
- **The Error:** `UnboundLocalError: local variable 'task_id'` or UI jumping to 100%.
- **Description:** High-frequency updates from synchronous download threads (`yt-dlp`) were overwhelming the `asyncio` event loop, causing logs to buffer and skip.
- **The Fix:** Decoupled the UI from the Worker threads. Engines now perform thread-safe dictionary updates to a global Registry. A separate background "Heartbeat" loop snapshots the Registry and performs throttled Telegram edits, ensuring UI stability and preventing FloodWait bans.

#### 🧱 Hurdle #45: The Ghost Message Persistence
- **The Error:** Status message remains in chat after all tasks are finished.
- **Description:** The loop lacked logic to detect an empty registry and perform self-destruction of the status entity.
- **The Fix:** Implemented a "Master Purge" in the worker's `finally` block and a "Lifecycle Watcher" in the `StatusManager`. The manager now detects `count == 0`, deletes the active status message, and enters a dormant state until a new task is registered.