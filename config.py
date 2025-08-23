import logging
from aiocache import SimpleMemoryCache

# ==================================================================
# 1. サーバー / uvicorn
# ==================================================================
SERVER_SETTINGS = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": True,
    "reload": False,
    "workers": 1,
    "log_level": "INFO",          # 文字列に統一（run.py で .lower() 可）
}

# ─── 旧コード互換 ───────────────────────────────
HOST       = SERVER_SETTINGS["host"]
PORT       = SERVER_SETTINGS["port"]
DEBUG      = SERVER_SETTINGS["debug"]
WORKERS    = SERVER_SETTINGS["workers"]
LOG_LEVEL  = SERVER_SETTINGS["log_level"]

# ==================================================================
# 2. ログ設定
# ==================================================================
LOGGING_SETTINGS = {
    "level": getattr(logging, SERVER_SETTINGS["log_level"].upper(), logging.INFO),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_path": None,          # None = コンソールのみ
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
    "allow_credentials": False,   # ワイルドカード使用時は必ず False
}

# ==================================================================
# 4. HTTP クライアント (httpx)
# ==================================================================
HTTP_SETTINGS = {
    "timeout": 20,
    "max_connections": 100,
    "max_keepalive_connections": 20,
    "keepalive_expiry": 5,
    "retries": 3,
}

# 旧単独定数（互換用）
HTTP_TIMEOUT       = HTTP_SETTINGS["timeout"]
MAX_CONNECTIONS    = HTTP_SETTINGS["max_connections"]

# ==================================================================
# 5. キャッシュ (aiocache)
# ==================================================================
CACHE_SETTINGS = {
    "backend": SimpleMemoryCache,   # クラスで保持
    "ttl_m3u8": 60,
    "ttl_segment": 300,
    "namespace": "proxy",
}

# ==================================================================
# 6. プロキシ
# ==================================================================
PROXY_SETTINGS = {
    "base_path": "proxy?url=",
    "url_safe_chars": "",          # urllib.parse.quote の safe
    "max_redirects": 5,
    "buffer_size": 8192,
}

# ==================================================================
# 7. レスポンス共通
# ==================================================================
RESPONSE_SETTINGS = {
    "m3u8_media_type": "application/vnd.apple.mpegurl",
    "default_media_type": "application/octet-stream",
    "error_messages": {
        "upstream_error":     "upstream error",
        "timeout_error":      "request timeout",
        "invalid_url":        "invalid URL",
        "extraction_failed":  "extraction failed",
    },
}

# ==================================================================
# 8. 正規表現パターン
# ==================================================================
REGEX_PATTERNS = {
    "uri_pattern":   r'URI="([^"]+)"',
    "url_validation": r'^https?://.+',
    "m3u8_line":     r'^#.*|^https?://.*\.ts$',
}

# ==================================================================
# 9. API エンドポイント
# ==================================================================
ENDPOINTS = {
    "health":         "/health",
    "extract":        "/extract",
    "proxy":          "/proxy",
    "stream_direct":  "/stream-direct",
    "batch_extract":  "/batch-extract",
    "playlist_info":  "/playlist-info",
    "channel_about":  "/channel-about",
    "related_videos": "/related-videos",
    "transcode":      "/transcode",
    "comments":      "/comments",
    "search":      "/search",
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
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        ),
        "po-token": "",        # ← 設定可能
        "X-YouTube-Client-Visitor-Id": "",  # ← 設定可能
    },
}

YTDLP_EXTRA = {
    "legacy_server_connect": False,
    "no_check_certificates": False,
    "prefer_insecure": False,
    "proxy": None,                      # 例 "http://127.0.0.1:8080"
    "external_downloader": None,        # 例 "aria2c"
    "external_downloader_args": None,   # 例 "-x 16 -k 1M"
}

# ==================================================================
# 11. ストリーム抽出関連
# ==================================================================
STREAM_EXTRACTION = {
    "supported_protocols": ["m3u8", "m3u8_native"],
    "m3u8_check_string": ".m3u8",
    "default_video_quality": "source",
    "audio_quality_prefix": "audio",
    "unknown_height_label": "?",
    "video_codec_none": "none",
    "max_streams": 50,
}

# ==================================================================
# 12. セキュリティ / デバッグ
# ==================================================================
SECURITY_SETTINGS = {
    "max_request_size": 1024 * 1024,  # 1 MB
    "rate_limit": {
        "enabled": False,
        "requests_per_minute": 60,
    },
}

DEBUG_SETTINGS = {
    "enable_debug_endpoints": False,
    "log_requests": True,
    "log_responses": False,
    "verbose_errors": False,
}

# ==================================================================
# 13. 後方互換エイリアス（旧コード用）
# ==================================================================
SERVER          = SERVER_SETTINGS
LOGGING         = LOGGING_SETTINGS
CORS            = CORS_SETTINGS
HTTP            = HTTP_SETTINGS
CACHE           = CACHE_SETTINGS
PROXY           = PROXY_SETTINGS
RESPONSE        = RESPONSE_SETTINGS
REGEX           = REGEX_PATTERNS
