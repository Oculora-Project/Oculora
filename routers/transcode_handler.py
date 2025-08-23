from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from yt_dlp import YoutubeDL
import logging
import config  # 必要に応じて設定を参照
from aiocache import cached, SimpleMemoryCache

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.get(config.ENDPOINTS["transcode"])
@cached(ttl=3600, cache=SimpleMemoryCache, key_builder=lambda f, video_url: f"tx:{video_url}")
def transcode(video_url: str = Query(..., description="YouTube動画URL")):
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get("url")
            if not stream_url:
                raise HTTPException(404, "動画ストリームURLが見つかりません")

            return JSONResponse({"transcode_url": stream_url})
    except Exception as e:
        logger.error(f"/transcode error: {e}")
        raise HTTPException(500, "変換用URL取得に失敗しました")
