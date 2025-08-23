import re
import logging
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode, quote

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from aiocache import cached, SimpleMemoryCache

import config
from routers.ytdlp_handler import run_ydl
from routers.extractor_util import get_stream_infos

router = APIRouter()
logger = logging.getLogger(__name__)

def normalize_youtube_url(url: str) -> str:
    """
    YouTube動画URLからv=動画IDだけを残した正規URLに変換
    """
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        video_ids = query.get("v")
        if video_ids:
            video_id = video_ids[0]
            new_query = urlencode({"v": video_id})
            path = "/watch"
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
        # 短縮URLや/embedパターン対応
        if parsed.netloc in ("youtu.be",):
            return f"https://www.youtube.com/watch?v={parsed.path.lstrip('/')}"
        if "embed" in parsed.path:
            v = parsed.path.split("/")[-1]
            return f"https://www.youtube.com/watch?v={v}"
        raise ValueError("v parameter not found")
    except Exception as e:
        logger.error(f"URL正規化失敗: {e}")
        raise

@cached(
    ttl=600,
    cache=SimpleMemoryCache,
    key_builder=lambda f, request, url: f"extract:{url}"
)
async def extract_cached(request: Request, url: str):
    normalized_url = normalize_youtube_url(url)
    if not re.match(config.REGEX_PATTERNS["url_validation"], normalized_url):
        raise HTTPException(
            400, config.RESPONSE_SETTINGS["error_messages"]["invalid_url"])

    # yt-dlpは同期コードなのでto_threadで非同期化
    import asyncio
    info = await asyncio.to_thread(run_ydl, normalized_url, {"skip_download": True, "quiet": True})

    meta = {
        "title":       info.get("title", "unknown"),
        "description": info.get("description"),
        "channel": {
            "name": info.get("uploader"),
            "id":   info.get("channel_id"),
            "url":  info.get("channel_url")
                     or (f"https://www.youtube.com/channel/{info.get('channel_id')}"
                        if info.get("channel_id") else None)
        },
        "view_count":  info.get("view_count"),
        "like_count":  info.get("like_count"),
        "upload_date": info.get("upload_date"),
        "duration":    info.get("duration"),
        "thumbnail":   info.get("thumbnail"),
    }

    streams = await asyncio.to_thread(get_stream_infos, normalized_url)
    if not streams:
        raise HTTPException(
            404, config.RESPONSE_SETTINGS["error_messages"]["extraction_failed"])

    return meta, streams, normalized_url

@router.get(config.ENDPOINTS["extract"])
async def extract(
    request: Request,
    url: str = Query(..., description="YouTube 動画 URL")
):
    """
    YouTube動画のメタ情報＋(プロキシ付)ストリーム一覧を返却
    {
      "meta": {...},
      "streams": [
        {"type":"video","quality":"720p","url":"http://<host>/proxy?..."},
        ...
      ]
    }
    """
    logger.info(f"[extract] request(original): {url}")
    try:
        meta, streams, normalized_url = await extract_cached(request, url)
        logger.info(f"[extract] request(normalized): {normalized_url}")

        # プロキシURL書き換え
        base_url = str(request.base_url).rstrip('/')
        proxy_base = f"{base_url}/{config.PROXY_SETTINGS['base_path']}"
        # safe_charsがconfigに存在しない場合は空文字列をデフォルトに
        safe_chars = config.PROXY_SETTINGS.get("url_safe_chars", "")

        for s in streams:
            s["url"] = proxy_base + quote(s["url"], safe=safe_chars)

        return JSONResponse({"meta": meta, "streams": streams}, media_type="application/json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[extract] error: {e}")
        raise HTTPException(
            500,
            config.RESPONSE_SETTINGS["error_messages"]["extraction_failed"]
        )

