import re
import collections
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from yt_dlp import YoutubeDL
from aiocache import cached, SimpleMemoryCache
import asyncio
import config

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(config.ENDPOINTS["related_videos"])
@cached(
    ttl=600,
    cache=SimpleMemoryCache,
    key_builder=lambda f, url, limit: f"rel:{url}:{limit}"
)
async def related_videos(
    url: str = Query(..., description="https://www.youtube.com/watch?v=..."),
    limit: int = Query(10, ge=1, le=50)
):
    if "youtube.com/watch" not in url:
        raise HTTPException(400, "invalid url")

    # blocking extraction using yt-dlp in thread
    def run_yt_dl_extract_1():
        with YoutubeDL(config.YTDLP_OPTIONS | {"skip_download": True, "quiet": True}) as ydl:
            return ydl.extract_info(url)

    info = await asyncio.to_thread(run_yt_dl_extract_1)
    text = (info.get("title", "") + " " + (info.get("description") or "")).lower()

    # 拡充したストップワードリスト（必要に応じて調整ください）
    stop = {
        "the", "and", "for", "to", "of", "in", "on", "at", "with", "from", "by", "is", "it",
        "this", "that", "you", "was", "are", "as", "be", "an", "have", "has", "i", "my",
        "に", "の", "を", "が", "は", "で", "と", "も", "な", "だ", "です", "から", "など"
    }

    # 日本語も含む単語抽出
    words = re.findall(r"[A-Za-z0-9\u3040-\u30ff\u4e00-\u9fff]+", text)
    # ストップワード除外かつ3文字以上の単語でフィルタ
    filtered_words = [w for w in words if w not in stop and len(w) > 2]

    # filtered_wordsが空なら元のwordsでフォールバック
    freq_words = filtered_words if filtered_words else [w for w in words if len(w) > 1]

    # 頻度カウントして上位5単語抽出
    freq = collections.Counter(freq_words)
    query = " ".join(w for w, _ in freq.most_common(5))

    # フォールバックでqueryが空ならタイトルを使う
    if not query.strip():
        query = info.get("title", "")

    def run_yt_dl_extract_2():
        search_opts = config.YTDLP_OPTIONS | {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
            "default_search": f"ytsearch{limit}",
        }
        with YoutubeDL(search_opts) as ydl:
            return ydl.extract_info(query)

    res = await asyncio.to_thread(run_yt_dl_extract_2)

    entries = []
    for e in res.get("entries", []):
        if e["id"] == info["id"]:
            continue
        entries.append({
            "id": e["id"],
            "title": e["title"],
            "url": f"https://www.youtube.com/watch?v={e['id']}",
            "duration": e.get("duration"),
            "channel": e.get("uploader"),
            "thumbnail": e.get("thumbnail"),
        })
        if len(entries) >= limit:
            break
    return JSONResponse(entries)
