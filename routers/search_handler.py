import logging
from typing import List, Dict
from fastapi import APIRouter, Query, HTTPException
from yt_dlp import YoutubeDL
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

def _search_with_ytdlp(query: str, limit: int) -> List[Dict]:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",  # メタ情報のみ
    }

    results = []
    with YoutubeDL(ydl_opts) as ydl:
        search_query = f"ytsearch{limit}:{query}"
        info = ydl.extract_info(search_query, download=False)
        entries = info.get("entries", [])

        for e in entries[:limit]:
            video_id = e.get("id")
            title = e.get("title")
            url = e.get("url")
            channel = e.get("channel")
            thumbnail = e.get("thumbnail")

            results.append({
                "id": video_id,
                "title": title,
                "url": url,
                "channel": channel,
                "thumbnail": thumbnail or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            })

    return results


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="検索クエリ文字列"),
    limit: int = Query(10, ge=1, le=50, description="最大取得件数")
):
    """
    yt-dlpを利用したYouTube検索APIです。
    検索ワードに対する動画情報を取得して返します。
    """
    try:
        # yt-dlpはブロッキングI/Oなのでasyncio.to_threadで非同期化
        results = await asyncio.to_thread(_search_with_ytdlp, q, limit)
        return results

    except Exception as e:
        logger.error(f"/search error: {e}", exc_info=True)
        raise HTTPException(500, "search operation failed")
