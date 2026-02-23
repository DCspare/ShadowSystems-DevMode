# apps/worker-video/handlers/mirror_leech_utils/download_utils/aria2_download.py
import logging

from shared.status_utils.aria2_status import Aria2Status

LOGGER = logging.getLogger("Aria2Download")


async def add_aria2_download(listener, url, dpath, filename=None):
    """
    WZML-Style Aria2 Downloader.
    Handles URI addition and initial Status Object registration.
    """
    # 1. Prepare Options (MLTB/WZML standard)
    a2c_opt = {
        "dir": dpath,
        "seed-time": "0",
        "allow-overwrite": "true",
        "check-certificate": "false",
    }
    if filename:
        a2c_opt["out"] = filename

    try:
        # 2. Add URI to Aria2 Daemon
        # Using the api instance attached to the listener (initialized in DownloadManager)
        download = listener.aria2_instance.add_uris([url], options=a2c_opt)
        gid = download.gid
    except Exception as e:
        LOGGER.error(f"Aria2 Add Error: {e}")
        await listener.on_error(str(e))
        return

    # 3. Create Status Object
    status = Aria2Status(gid, listener, listener.aria2_instance)

    LOGGER.info(f"📥 Aria2 Download Started. GID: {gid} | ID: {listener.task_id}")

    # 4. Notify Listener with the Object
    await listener.on_download_start(status)  # ✅ Pass the status object
