# routers/playlist_handler.py
import logging
from fastapi import APIRouter, HTTPException, Query
from yt_dlp import YoutubeDL
from aiocache import cached, SimpleMemoryCache 

import config

logger = logging.getLogger(__name__)
router = APIRouter()


@cached(ttl=600, cache=SimpleMemoryCache, key_builder=lambda f, playlist_url: f"pl:{playlist_url}")
def playlist_info(
    playlist_url: str = Query(..., description="https://www.youtube.com/playlist?list=...")
):
    """
    プレイリスト内の各動画メタをフラット抽出して返す。
    """
    ydl_opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    if "entries" not in info:
        raise HTTPException(404, "playlist not found")

    items = [{
        "id": e["id"],
        "title": e.get("title"),
        "duration": e.get("duration_string") or e.get("duration"),
        "thumbnail": e.get("thumbnail"),
        "url": f"https://www.youtube.com/watch?v={e['id']}"
    } for e in info["entries"]]

    return items
