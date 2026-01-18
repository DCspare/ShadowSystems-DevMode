# apps/shared/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# --- HELPER SUB-SCHEMAS (Atomic Parts) ---

class FileVisuals(BaseModel):
    poster: Optional[str] = None            # Telegram File ID
    backdrop: Optional[str] = None
    trailer_key: Optional[str] = None       # ➕ NEW: For Auto-Trailers / Hero Loop
    screenshots: List[str] = []

class CastMember(BaseModel):                # ➕ NEW: For Content Enrichment
    tmdb_id: int                            # Primary Key
    name: str
    role: str
    image: Optional[str] = None

class SubtitleTrack(BaseModel):
    lang: str
    index: int 

class AudioTrackInfo(BaseModel): # ➕ NEW: Audio Metadata
    lang: str
    codec: str # e.g. aac, ac3, eac3
    channels: float # 2.0, 5.1, 7.1
    index: int

class EmbedLink(BaseModel):
    host: str
    url: str
    priority: int = 1

class BackupLink(BaseModel):
    host: str                             # Gofile, PixelDrain
    url: str
    icon: Optional[str] = None
    status: str = "active"

class IntroTimings(BaseModel):
    start: int
    end: int
    votes: int = 0

class FileData(BaseModel):
    quality: str = "720p"
    label: Optional[str] = None 
    size_human: Optional[str] = None
    telegram_id: str
    file_size: int
    file_hash: Optional[str] = None       # For Nginx Cache checking // VIP Source (ShadowStream)
    mime_type: str

    # ➕ CRITICAL: RAW MTPROTO KEYS (Required for Go Engine/gotgproto)
    tg_raw: Dict[str, Any]
    
    # ➕ Enriched Fields
    subtitles: List[SubtitleTrack] = [] # Stream #0:3
    # (Free Tier)
    embeds: List[EmbedLink] = []        # VidHide, StreamTape
    downloads: List[BackupLink] = []    # Gofile, PixelDrain (Archive Page)
    added_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp())) # (Unix Timestamp) for sorting performance

class SignRequest(BaseModel):
    short_id: str   # The Movie Page
    file_id: str    # The Specific Video File the user wants
    # Optional: guest_token or captcha_token for future rate-limiting

# --- CONTENT SUB-SCHEMAS (Series/Manga Logic) ---

class SeasonPack(BaseModel):
    season: int
    zip_file_id: str
    size: str

class Episode(BaseModel):
    episode: int
    title: str
    overview: Optional[str] = None     # ➕ NEW: Episode Plot
    still_path: Optional[str] = None   # ➕ NEW: Specific Episode Thumbnail
    file_id: str
    quality: str

class MangaChapter(BaseModel):
    chap: float
    title: str
    storage_id: str
    pages: List[str]

# --- 🎵 MUSIC ENGINE (ShadowTunes) ➕ NEW ---

class AudioTrack(BaseModel):
    track_num: int
    title: str
    artist: Optional[str] = None
    duration: int
    telegram_file_id: str
    stream_url: Optional[str] = None

class MusicAlbum(BaseModel):
    # _id will be "album_unique_name"
    linked_tmdb_id: Union[int, str] # Connects to Movie/Anime
    type: str = "album"
    title: str
    artist: str
    year: Optional[int] = None
    cover_image: Optional[str] = None
    tracks: List[AudioTrack] = []
    zip_file_id: Optional[str] = None # For GPlinks download

# --- 📽️ MAIN LIBRARY ENTITY ---

class LibraryItem(BaseModel):
    # Define _id by PyObjectId logic in motor
    tmdb_id: int                    # Primary Key
    short_id: str                   # 7-char slug
    media_type: str                 # movie | series | manga

    title: str
    clean_title: str
    year: Optional[int] = None
    genres: List[str] = []
    rating: float = 0.0     # # rating = The external Score (TMDB 3.5/10)
    status: str = "processing"      # available | processing | banned | repairing
    
    intro_timings: Optional[IntroTimings] = None     # { "start": 90, "end": 150, "votes": 5 }, Timestamp in seconds
    visuals: FileVisuals = FileVisuals()
    cast: List[CastMember] = []     # ➕ NEW
    
    # Content Buckets
    files: List[FileData] = []      # Movies

    # Series (Multi)
    total_seasons: Optional[int] = None
    season_packs: Optional[List[SeasonPack]] = []
    seasons: Optional[Dict[str, List[Episode]]] = None 

    # Manga (Multi)
    chapter_count: Optional[int] = None
    content_rating: str = "safe"    # safe | 18+
    chapters: Optional[List[MangaChapter]] = []

    # e.g., ["marvel_phase_1", "best_horror_2024"]
    collections: List[str] = []

# --- 👥 USER & IDENTITY ---

class DeviceLock(BaseModel):
    hash: str
    locked_at: datetime

class UserHistoryItem(BaseModel):
    # Unified History
    tmdb_id: Optional[Union[str, int]] = None
    timestamp: int # Video second
    # for Manga
    last_chap: Optional[float] = None # Manga
    last_page: Optional[int] = None   # Manga
    updated_at: datetime

class Referral(BaseModel):
    code: str
    invited_count: int = 0
    invited_by: Optional[int] = None

class UserSecurity(BaseModel):
    auth_token_secret: str
    active_sessions: int = 0        # Redis counter sync
    bound_device: Optional[DeviceLock] = None

class User(BaseModel):
    id: Union[int, str] # ➕ CHANGED: Supports Telegram INT and Guest "string_hash"
    type: str = "telegram"
    tenant_id: Optional[str] = None # ➕ NEW: Franchise ownership
    role: str = "free"              # free | premium | admin

    premium_until: Optional[datetime] = None # ➕ NEW: VIP Expiry
    
    security: UserSecurity = UserSecurity(auth_token_secret="")
    history: Dict[str, UserHistoryItem] = {}

    # Growth & Notification Tags (OneSignal)
    referral_code: Optional[str] = None
    invited_by: Optional[Union[int, str]] = None
    points: int = 0
    # Examples: ["waiting:tmdb_123", "sub:manga_999"]
    notification_tags: List[str] = []

# --- 🏗️ THE WORKER SWARM ---

class WorkerState(BaseModel):
    api_id: str = "1" # Identifier (e.g. worker_video_1)
    phone_hash: str   # To track which SIM is active
    status: str = "active" # active | flood_wait | dead
    flood_wait_until: Optional[datetime] = None

    # ➕ NEW: Warmer Logic
    warming_phase: int = 0

    current_task: Optional[str] = None
    ipv6_address: Optional[str] = None              # For auditing IP rotation

# --- 🚑 THE MEDIC (REPORTS) ---

class Report(BaseModel):
    target_id: int
    issue: str                                     # dead_link | wrong_audio | missing_pages 
    status: str = "pending"                        # pending | fixed

# --- 💬 COMMENTS (GHOST SYSTEM) ---

class Comment(BaseModel):
    target_id: str                      # ID of Movie, Series, or Manga Chapter
    user_id: int                        # Links to Users Collection (Guest Cookie or Telegram ID)
    nickname: str                       # Auto-generated if Guest
    avatar_seed: str                    # Seed for DiceBear deterministic avatars
    body: str                           # That ending was insane! >!Spoiler Text!<",
    is_spoiler: bool = False            # If true, blurred until clicked
    timestamp: Optional[int] = None     # (Optional) Video second for "Timeline Comments"
    likes: int = 0
    created_at: datetime
    moderation_status: str = "active"   # active | flagged | deleted

# --- 🗳️ REQUEST HUB ---
class ContentRequest(BaseModel):
    tmdb_id: int
    title: str
    media_type: str
    requested_by_users: List[Union[int, str]] # List of User IDs who voted
    vote_count: int = 0         # vote_count = Internal User Votes (Request Hub / Likes)
    status: str = "pending" # pending | filled | rejected
    created_at: datetime

# --- 🏢 B2B FRANCHISE ---

class TenantAddons(BaseModel):
    android_app: Dict[str, Any] = {"active": False}
    dmca_shield: Dict[str, Any] = {"active": False}
    capacity: Dict[str, int] = {"tier": 1}

class TenantStats(BaseModel):
    monthly_visitors: int = 0
    bandwidth_used_gb: float = 0.0
    revenue_generated: float = 0.0

class Tenant(BaseModel):
    domain: str
    owner_email: str
    plan: str           # rev_share | fixed_fee
    status: str = "active"      # active | suspended | past_due
    addons: TenantAddons = TenantAddons()

    # Resources
    resource_pool: Dict[str, Any] = {} # { "worker_ids": ["w1", "w2"] }
    
    # Billing
    subscription: Dict[str, Any] = {} 
    stats: TenantStats = TenantStats()
    next_billing_date: Optional[datetime] = None
    auto_suspend: bool = True

    # Ads (Includes VAST)
    ad_codes: Dict[str, str] = {}