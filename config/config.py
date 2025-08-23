import os
import logging
from typing import Dict, Any
from aiocache import SimpleMemoryCache

# 環境変数読み込みヘルパー
def get_env_bool(key: str, default: bool = False) -> bool:
    """環境変数をbool型で取得"""
    return os.getenv(key, str(default)).lower() in ('true', '1', 'yes', 'on')

def get_env_int(key: str, default: int) -> int:
    """環境変数をint型で取得"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_str(key: str, default: str = "") -> str:
    """環境変数をstr型で取得"""
    return os.getenv(key, default)

# ==================================================================
# 1. サーバー / uvicorn
# ==================================================================

SERVER_SETTINGS = {
    "host": get_env_str("HOST", "0.0.0.0"),
    "port": get_env_int("PORT", 8000),
    "debug": get_env_bool("DEBUG", True),
    "reload": get_env_bool("RELOAD", False),
    "workers": get_env_int("WORKERS", 1),
    "log_level": get_env_str("LOG_LEVEL", "INFO"),
}

# ─── 旧コード互換 ───────────────────────────────
HOST = SERVER_SETTINGS["host"]
PORT = SERVER_SETTINGS["port"]
DEBUG = SERVER_SETTINGS["debug"]
WORKERS = SERVER_SETTINGS["workers"]
LOG_LEVEL = SERVER_SETTINGS["log_level"]

# ==================================================================
# 2. ログ設定
# ==================================================================

LOGGING_SETTINGS = {
    "level": getattr(logging, SERVER_SETTINGS["log_level"].upper(), logging.INFO),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_path": None,  # None = コンソールのみ
    "max_file_size": 10 * 1024 * 1024,
    "backup_count": 5,
}

# ==================================================================
# 3. CORS
# ==================================================================

CORS_SETTINGS = {
    "allow_origins": ["*"],
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "allow_credentials": False,  # ワイルドカード使用時は必ず False
}

# ==================================================================
# 4. HTTP クライアント (httpx)
# ==================================================================

HTTP_SETTINGS = {
    "timeout": get_env_int("HTTP_TIMEOUT", 20),
    "max_connections": get_env_int("MAX_CONNECTIONS", 100),
    "max_keepalive_connections": get_env_int("MAX_KEEPALIVE_CONNECTIONS", 20),
    "keepalive_expiry": get_env_int("KEEPALIVE_EXPIRY", 5),
    "retries": get_env_int("HTTP_RETRIES", 3),
}

# 旧単独定数（互換用）
HTTP_TIMEOUT = HTTP_SETTINGS["timeout"]
MAX_CONNECTIONS = HTTP_SETTINGS["max_connections"]

# ==================================================================
# 5. キャッシュ (aiocache)
# ==================================================================

CACHE_SETTINGS = {
    "backend": SimpleMemoryCache,  # クラスで保持
    "ttl_m3u8": get_env_int("CACHE_TTL_M3U8", 60),
    "ttl_segment": get_env_int("CACHE_TTL_SEGMENT", 300),
    "namespace": get_env_str("CACHE_NAMESPACE", "proxy"),
}

# ==================================================================
# 6. プロキシ
# ==================================================================

PROXY_SETTINGS = {
    "base_path": get_env_str("PROXY_BASE_PATH", "proxy?url="),
    "url_safe_chars": get_env_str("PROXY_URL_SAFE_CHARS", ""),
    "max_redirects": get_env_int("PROXY_MAX_REDIRECTS", 5),
    "buffer_size": get_env_int("PROXY_BUFFER_SIZE", 8192),
}

# ==================================================================
# 7. レスポンス共通
# ==================================================================

RESPONSE_SETTINGS = {
    "m3u8_media_type": "application/vnd.apple.mpegurl",
    "default_media_type": "application/octet-stream",
    "error_messages": {
        "upstream_error": "upstream error",
        "timeout_error": "request timeout",
        "invalid_url": "invalid URL",
        "extraction_failed": "extraction failed",
    },
}

# ==================================================================
# 8. 正規表現パターン
# ==================================================================

REGEX_PATTERNS = {
    "uri_pattern": r'URI="([^"]+)"',
    "url_validation": r'^https?://.+',
    "m3u8_line": r'^#.*|^https?://.*\.ts$',
}

# ==================================================================
# 9. API エンドポイント
# ==================================================================

ENDPOINTS = {
    "health": "/health",
    "extract": "/extract",
    "proxy": "/proxy",
    "stream_direct": "/stream-direct",
    "batch_extract": "/batch-extract",
    "playlist_info": "/playlist-info",
    "channel_about": "/channel-about",
    "related_videos": "/related-videos",
    "transcode": "/transcode",
    "comments": "/comments",
    "search": "/search",
}

# ==================================================================
# 10. yt-dlp 共通オプション
# ==================================================================

YTDLP_OPTIONS = {
    "quiet": True,
    "skip_download": True,
    "forceurl": True,
    "simulate": True,
    "no_warnings": True,
    "extract_flat": False,
    "ignoreerrors": True,
    "skipmanifest": True,
    "http_headers": {
        "User-Agent": get_env_str(
            "YTDLP_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        ),
        "po-token": get_env_str("YTDLP_PO_TOKEN", ""),
        "X-YouTube-Client-Visitor-Id": get_env_str("YTDLP_CLIENT_VISITOR_ID", ""),
    },
}

YTDLP_EXTRA = {
    "legacy_server_connect": get_env_bool("YTDLP_LEGACY_SERVER_CONNECT", False),
    "no_check_certificates": get_env_bool("YTDLP_NO_CHECK_CERTIFICATES", False),
    "prefer_insecure": get_env_bool("YTDLP_PREFER_INSECURE", False),
    "proxy": get_env_str("YTDLP_PROXY") or None,
    "external_downloader": get_env_str("YTDLP_EXTERNAL_DOWNLOADER") or None,
    "external_downloader_args": get_env_str("YTDLP_EXTERNAL_DOWNLOADER_ARGS") or None,
}

# ==================================================================
# 11. ストリーム抽出関連
# ==================================================================

STREAM_EXTRACTION = {
    "supported_protocols": ["m3u8", "m3u8_native"],
    "m3u8_check_string": ".m3u8",
    "default_video_quality": get_env_str("STREAM_DEFAULT_VIDEO_QUALITY", "source"),
    "audio_quality_prefix": get_env_str("STREAM_AUDIO_QUALITY_PREFIX", "audio"),
    "unknown_height_label": get_env_str("STREAM_UNKNOWN_HEIGHT_LABEL", "?"),
    "video_codec_none": "none",
    "max_streams": get_env_int("STREAM_MAX_STREAMS", 50),
}

# ==================================================================
# 12. セキュリティ / デバッグ
# ==================================================================

SECURITY_SETTINGS = {
    "max_request_size": get_env_int("MAX_REQUEST_SIZE", 1024 * 1024),  # 1 MB
    "rate_limit": {
        "enabled": get_env_bool("RATE_LIMIT_ENABLED", False),
        "requests_per_minute": get_env_int("RATE_LIMIT_REQUESTS_PER_MINUTE", 60),
    },
}

DEBUG_SETTINGS = {
    "enable_debug_endpoints": get_env_bool("DEBUG_ENABLE_DEBUG_ENDPOINTS", False),
    "log_requests": get_env_bool("DEBUG_LOG_REQUESTS", True),
    "log_responses": get_env_bool("DEBUG_LOG_RESPONSES", False),
    "verbose_errors": get_env_bool("DEBUG_VERBOSE_ERRORS", False),
}

# ==================================================================
# 13. 後方互換エイリアス（旧コード用）
# ==================================================================

SERVER = SERVER_SETTINGS
LOGGING = LOGGING_SETTINGS
CORS = CORS_SETTINGS
HTTP = HTTP_SETTINGS
CACHE = CACHE_SETTINGS
PROXY = PROXY_SETTINGS
RESPONSE = RESPONSE_SETTINGS
REGEX = REGEX_PATTERNS
