import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from aiocache import cached, SimpleMemoryCache
import config
from routers.ytdlp_handler import run_ydl

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(config.ENDPOINTS["stream_direct"])
@cached(ttl=1800, cache=SimpleMemoryCache, key_builder=lambda f, video_url: f"m3u8:{video_url}")
def stream_direct(
    video_url: str = Query(..., description="YouTube 動画 URL")
):
    """
    指定動画の HLS マニフェスト (.m3u8) URL を 1 本だけ返す。

    例:
      GET /stream-direct?video_url=https://www.youtube.com/watch?v=xxxx
      → { "url": "https://...index.m3u8" }
    """
    try:
        info = run_ydl(video_url, custom={
            "skip_download": True,
            "quiet": True,
            "allow_unplayable_formats": True
        })

        for fmt in info.get("formats", []):
            m3u8_url = fmt.get("url") or ""
            if ".m3u8" in m3u8_url:
                return JSONResponse({"url": m3u8_url})

        raise HTTPException(404, "no m3u8 manifest found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[stream-direct] error: {e}")
        raise HTTPException(500, "extraction failed")
