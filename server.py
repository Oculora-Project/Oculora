import re, asyncio, logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from routers.proxy_handler import router as proxy_router
from routers.batch_handler    import router as batch_router
from routers.playlist_handler import router as playlist_router
from routers.channel_handler  import router as channel_router
from routers.related_handler  import router as related_router
from routers.transcode_handler import router as transcode_router
from routers.stream_direct_handler  import router as stream_direct_router
from routers.extract_handler      import router as extract_router
from routers.health_handler import router as health_router
from routers.comments_handler import router as comments_router
from routers.search_handler import router as search_router

import config

# ────────────────  共通設定・初期化 ────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(level=config.LOGGING_SETTINGS["level"],
                    format=config.LOGGING_SETTINGS["format"])

app = FastAPI(title="Oculora Project",
              version="1.0.4",
              debug=config.SERVER_SETTINGS["debug"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_SETTINGS["allow_origins"],
    allow_methods=config.CORS_SETTINGS["allow_methods"],
    allow_headers=config.CORS_SETTINGS["allow_headers"],
    allow_credentials=config.CORS_SETTINGS["allow_credentials"]
)

URI_RE = re.compile(config.REGEX_PATTERNS["uri_pattern"])
http_limits = httpx.Limits(max_connections=config.HTTP_SETTINGS["max_connections"],
                           max_keepalive_connections=config.HTTP_SETTINGS["max_keepalive_connections"],
                           keepalive_expiry=config.HTTP_SETTINGS["keepalive_expiry"])

# ──────────────────────
# 汎用フェッチ
# ──────────────────────
async def fetch(url: str, headers: dict):
    """HTTP GETリクエストを実行"""
    timeout = config.HTTP_SETTINGS["timeout"]
    retries = config.HTTP_SETTINGS["retries"]
    
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(limits=http_limits) as client:
                r = await client.get(url, headers=headers, timeout=timeout)
                if r.status_code != 200:
                    error_msg = config.RESPONSE_SETTINGS["error_messages"]["upstream_error"]
                    raise HTTPException(r.status_code, error_msg)
                return r
        except httpx.TimeoutException:
            if attempt == retries:
                error_msg = config.RESPONSE_SETTINGS["error_messages"]["timeout_error"]
                logger.error(f"Request timeout after {retries} retries: {url}")
                raise HTTPException(408, error_msg)
            logger.warning(f"Timeout on attempt {attempt + 1} for {url}, retrying...")
            await asyncio.sleep(1)  # 1秒待機してリトライ

# ──────────────────────
# エンドポイント系
# ──────────────────────
app.include_router(proxy_router)
app.include_router(extract_router)
app.include_router(batch_router)
app.include_router(playlist_router)
app.include_router(channel_router)
app.include_router(related_router)
app.include_router(transcode_router)
app.include_router(stream_direct_router)
app.include_router(health_router)
app.include_router(comments_router)
app.include_router(search_router)

# ──────────────────────
# アプリケーション起動設定
# ──────────────────────
if __name__ == "__main__":
    import uvicorn
    
    server_config = config.SERVER_SETTINGS
    
    logger.info(f"Starting server on {server_config['host']}:{server_config['port']}")
    
    uvicorn.run(
        "main:app",
        host=server_config["host"],
        port=server_config["port"],
        debug=server_config["debug"],
        reload=server_config["reload"],
        workers=server_config["workers"],
        log_level=logging.getLevelName(config.LOGGING_SETTINGS["level"]).lower()
    )
