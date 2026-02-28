# apps/shared/schemas.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- HELPER SUB-SCHEMAS (Atomic Parts) ---


class FileVisuals(BaseModel):
    poster: str | None = None  # Telegram File ID
    backdrop: str | None = None
    trailer_key: str | None = None  # ➕ NEW: For Auto-Trailers / Hero Loop
    screenshots: list[str] = []


class CastMember(BaseModel):  # ➕ NEW: For Content Enrichment
    tmdb_id: int  # Primary Key
    name: str
    role: str
    image: str | None = None


class SubtitleTrack(BaseModel):
    lang: str
    index: int


class AudioTrackInfo(BaseModel):  # ➕ NEW: Audio Metadata
    lang: str
    codec: str  # e.g. aac, ac3, eac3
    channels: float  # 2.0, 5.1, 7.1
    index: int


class EmbedLink(BaseModel):
    host: str
    url: str
    priority: int = 1


class BackupLink(BaseModel):
    host: str  # Gofile, PixelDrain
    url: str
    icon: str | None = None
    status: str = "active"


class IntroTimings(BaseModel):
    start: int
    end: int
    votes: int = 0


class FileData(BaseModel):
    quality: str = "720p"
    label: str | None = None
    size_human: str | None = None
    telegram_id: str
    file_size: int
    file_hash: str | None = (
        None  # For Nginx Cache checking // VIP Source (ShadowStream)
    )
    mime_type: str

    # ➕ CRITICAL: RAW MTPROTO KEYS (Required for Go Engine/gotgproto)
    tg_raw: dict[str, Any]

    # ➕ Enriched Fields
    subtitles: list[SubtitleTrack] = []  # Stream #0:3
    # (Free Tier)
    embeds: list[EmbedLink] = []  # VidHide, StreamTape
    downloads: list[BackupLink] = []  # Gofile, PixelDrain (Archive Page)
    added_at: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp())
    )  # (Unix Timestamp) for sorting performance


class SignRequest(BaseModel):
    short_id: str  # The Movie Page
    file_id: str  # The Specific Video File the user wants
    # Optional: guest_token or captcha_token for future rate-limiting


# --- CONTENT SUB-SCHEMAS (Series/Manga Logic) ---


class SeasonPack(BaseModel):
    season: int
    zip_file_id: str
    size: str


class Episode(BaseModel):
    episode: int
    title: str
    overview: str | None = None  # ➕ NEW: Episode Plot
    still_path: str | None = None  # ➕ NEW: Specific Episode Thumbnail
    file_id: str
    quality: str


class MangaChapter(BaseModel):
    chap: float
    title: str
    storage_id: str
    pages: list[str]


# --- 🎵 MUSIC ENGINE (ShadowTunes) ➕ NEW ---


class AudioTrack(BaseModel):
    track_num: int
    title: str
    artist: str | None = None
    duration: int
    telegram_file_id: str
    stream_url: str | None = None


class MusicAlbum(BaseModel):
    # _id will be "album_unique_name"
    linked_tmdb_id: int | str  # Connects to Movie/Anime
    type: str = "album"
    title: str
    artist: str
    year: int | None = None
    cover_image: str | None = None
    tracks: list[AudioTrack] = []
    zip_file_id: str | None = None  # For GPlinks download


# --- 📽️ MAIN LIBRARY ENTITY ---


class LibraryItem(BaseModel):
    # Define _id by PyObjectId logic in motor
    tmdb_id: int  # Primary Key
    imdb_id: str | None = None  # Optional
    short_id: str  # 7-char slug
    media_type: str  # movie | series | manga

    title: str
    clean_title: str
    year: int | None = None
    genres: list[str] = []
    rating: float = 0.0  # # rating = The external Score (TMDB 3.5/10)
    status: str = "processing"  # available | processing | banned | repairing

    popularity: float | None = None
    airing_status: str | None = None  # Currently Airing, Released, etc.
    tagline: str | None = None
    runtime: str | None = None  # Display ready: "24 min per ep"
    tagline: str | None = None
    rank: int | None = None
    season_name: str | None = None  # For Anime "summer", "winter"
    budget: str | None = None  # For Movies
    revenue: str | None = None  # For Movies
    broadcast: str | None = None  # For Anime
    source: str | None = None  # For Anime"Manga", "Light Novel"
    created_by: list[str] = []  # For TV (Directors/Creators)

    # Dates & Stats
    release_date: str | None = None  # For TV
    first_air_date: str | None = None  # For TV
    last_air_date: str | None = None  # For TV
    total_episodes: int | None = None  # For TV
    total_seasons: int | None = None  # For TV

    # Complex Titles
    titles: dict[str, Any] = {}  # english, japanese, synonyms

    intro_timings: IntroTimings | None = (
        None  # { "start": 90, "end": 150, "votes": 5 }, Timestamp in seconds
    )
    visuals: FileVisuals = FileVisuals()
    cast: list[CastMember] = []  # ➕ NEW

    # Content Buckets
    files: list[FileData] = []  # Movies

    # Series (Multi)
    season_packs: list[SeasonPack] | None = []
    seasons: dict[str, list[Episode]] | None = None

    # Manga (Multi)
    chapter_count: int | None = None
    content_rating: str = "safe"  # safe | 18+
    chapters: list[MangaChapter] | None = []

    # e.g., ["marvel_phase_1", "best_horror_2024"]
    collections: list[str] = []


# --- 👥 USER & IDENTITY ---


class DeviceLock(BaseModel):
    hash: str
    locked_at: datetime


class UserHistoryItem(BaseModel):
    # Unified History
    tmdb_id: str | int | None = None
    timestamp: int  # Video second
    # for Manga
    last_chap: float | None = None  # Manga
    last_page: int | None = None  # Manga
    updated_at: datetime


class Referral(BaseModel):
    code: str
    invited_count: int = 0
    invited_by: int | None = None


class UserSecurity(BaseModel):
    auth_token_secret: str
    active_sessions: int = 0  # Redis counter sync
    bound_device: DeviceLock | None = None


class User(BaseModel):
    id: int | str  # ➕ CHANGED: Supports Telegram INT and Guest "string_hash"
    type: str = "telegram"
    tenant_id: str | None = None  # ➕ NEW: Franchise ownership
    role: str = "free"  # free | premium | admin

    premium_until: datetime | None = None  # ➕ NEW: VIP Expiry

    security: UserSecurity = UserSecurity(auth_token_secret="")
    history: dict[str, UserHistoryItem] = {}

    # Growth & Notification Tags (OneSignal)
    referral_code: str | None = None
    invited_by: int | str | None = None
    points: int = 0
    # Examples: ["waiting:tmdb_123", "sub:manga_999"]
    notification_tags: list[str] = []


# --- 🏗️ THE WORKER SWARM ---


class WorkerState(BaseModel):
    api_id: str = "1"  # Identifier (e.g. worker_video_1)
    phone_hash: str  # To track which SIM is active
    status: str = "active"  # active | flood_wait | dead
    flood_wait_until: datetime | None = None

    # ➕ NEW: Warmer Logic
    warming_phase: int = 0

    current_task: str | None = None
    ipv6_address: str | None = None  # For auditing IP rotation


# --- 🚑 THE MEDIC (REPORTS) ---


class Report(BaseModel):
    target_id: int
    issue: str  # dead_link | wrong_audio | missing_pages
    status: str = "pending"  # pending | fixed


# --- 💬 COMMENTS (GHOST SYSTEM) ---


class Comment(BaseModel):
    target_id: str  # ID of Movie, Series, or Manga Chapter
    user_id: int  # Links to Users Collection (Guest Cookie or Telegram ID)
    nickname: str  # Auto-generated if Guest
    avatar_seed: str  # Seed for DiceBear deterministic avatars
    body: str  # That ending was insane! >!Spoiler Text!<",
    is_spoiler: bool = False  # If true, blurred until clicked
    timestamp: int | None = None  # (Optional) Video second for "Timeline Comments"
    likes: int = 0
    created_at: datetime
    moderation_status: str = "active"  # active | flagged | deleted


# --- 🗳️ REQUEST HUB ---
class ContentRequest(BaseModel):
    tmdb_id: int
    title: str
    media_type: str
    requested_by_users: list[int | str]  # List of User IDs who voted
    vote_count: int = 0  # vote_count = Internal User Votes (Request Hub / Likes)
    status: str = "pending"  # pending | filled | rejected
    created_at: datetime


# --- 🏢 B2B FRANCHISE ---


class TenantAddons(BaseModel):
    android_app: dict[str, Any] = {"active": False}
    dmca_shield: dict[str, Any] = {"active": False}
    capacity: dict[str, int] = {"tier": 1}


class TenantStats(BaseModel):
    monthly_visitors: int = 0
    bandwidth_used_gb: float = 0.0
    revenue_generated: float = 0.0


class Tenant(BaseModel):
    domain: str
    owner_email: str
    plan: str  # rev_share | fixed_fee
    status: str = "active"  # active | suspended | past_due
    addons: TenantAddons = TenantAddons()

    # Resources
    resource_pool: dict[str, Any] = {}  # { "worker_ids": ["w1", "w2"] }

    # Billing
    subscription: dict[str, Any] = {}
    stats: TenantStats = TenantStats()
    next_billing_date: datetime | None = None
    auto_suspend: bool = True

    # Ads (Includes VAST)
    ad_codes: dict[str, str] = {}
