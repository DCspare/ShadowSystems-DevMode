# apps/shared/ext_utils/status_utils.py

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_UPLOADING = "Uploading"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Paused"
    STATUS_ARCHIVING = "Archiving"
    STATUS_EXTRACTING = "Extracting"
    STATUS_SPLITTING = "Splitting"
    STATUS_CHECKING = "Checking"
    STATUS_SEEDING = "Seeding"
    STATUS_PROCESSING = "Processing"
    STATUS_FAILED = "Failed"
    STATUS_CANCELLED = "Cancelled"
    STATUS_COMPLETED = "Completed"


def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return "0B"
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"


def get_readable_time(seconds: int):
    if seconds is None or seconds < 0:
        return "∞"
    periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f"{int(period_value)}{period_name}"
    return result or "0s"


def speed_string_to_bytes(size_text: str):
    """
    WZML-X Helper: Converts strings like '10.5 MB' into raw bytes.
    Required by Direct Link Generators.
    """
    size = 0
    size_text = size_text.lower()
    if "k" in size_text:
        size += float(size_text.split("k")[0]) * 1024
    elif "m" in size_text:
        size += float(size_text.split("m")[0]) * 1048576
    elif "g" in size_text:
        size += float(size_text.split("g")[0]) * 1073741824
    elif "t" in size_text:
        size += float(size_text.split("t")[0]) * 1099511627776
    elif "b" in size_text:
        size += float(size_text.split("b")[0])
    return size


def get_progress_bar_string(pct):
    try:
        pct = float(str(pct).strip("%"))
    except:
        pct = 0
    p = min(max(pct, 0), 100)
    cFull = int(p // 8.33)  # 12 bars total
    return f"[{'■' * cFull}{'□' * (12 - cFull)}]"


def aria2_name(download):
    """WZML-X Helper to get name from aria2 download object."""
    if not download.files:
        return "Metadata"
    return download.files[0].path.split("/")[-1] or "Aria2_Task"


def is_metadata(download):
    """WZML-X Helper to check if aria2 is in metadata phase."""
    return download.followed_by is not None
