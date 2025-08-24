# routers/channel_handler.py
import re, json, logging, httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import config
from aiocache import cached, SimpleMemoryCache

logger = logging.getLogger(__name__)
router = APIRouter()

# ── 内部 util（ytInitialData 取得） ─────────
async def _fetch_initial_data(page_url: str) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.get(page_url)
    if r.status_code != 200:
        raise HTTPException(r.status_code, "upstream error")
    import re
    m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});", r.text, re.S)
    if not m:
        raise HTTPException(500, "parse error")
    return json.loads(m.group(1))

# ── /channel-about ────────────────────────
@router.get(config.ENDPOINTS["channel_about"])
@cached(ttl=1800, cache=SimpleMemoryCache, key_builder=lambda f, channel_url: f"about:{channel_url}")
async def channel_about(
    channel_url: str = Query(..., description="https://www.youtube.com/@<handle> or UCxxxx")
):
    # channel_url がハンドル or チャンネルIDかを判定
    if channel_url.startswith("UC") and len(channel_url) >= 20:
        base_url = f"https://www.youtube.com/channel/{channel_url}"
    elif re.match(r"^https://(www\.)?youtube\.com/@.+", channel_url):
        base_url = channel_url
    else:
        raise HTTPException(400, "invalid channel url or id")

    # about データ
    about_data = await _fetch_initial_data(base_url + "/about")
    # video データ
    video_data = await _fetch_initial_data(base_url + "/videos")

    try:
        meta = about_data["metadata"]["channelMetadataRenderer"]

        # 最近の動画5本を抽出
        videos = []
        contents = (
            video_data
            .get("contents", {})
            .get("twoColumnBrowseResultsRenderer", {})
            .get("tabs", [])[1]  # "動画" タブ
            .get("tabRenderer", {})
            .get("content", {})
            .get("richGridRenderer", {})
            .get("contents", [])
        )
        for item in contents:
            vid = item.get("richItemRenderer", {}).get("content", {}).get("videoRenderer")
            if not vid:
                continue
            videos.append({
                "video_id": vid.get("videoId"),
                "title": vid.get("title", {}).get("runs", [{}])[0].get("text"),
                "thumbnail": vid.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url"),
                "published": vid.get("publishedTimeText", {}).get("simpleText"),
                "view_count": vid.get("viewCountText", {}).get("simpleText"),
                "url": f"https://www.youtube.com/watch?v={vid.get('videoId')}"
            })
            if len(videos) >= 5:
                break

        return JSONResponse({
            "title":       meta["title"],
            "description": meta.get("description"),
            "subscriber":  meta.get("subscriberCountText", {}).get("simpleText"),
            "avatar":      meta["avatar"]["thumbnails"][-1]["url"],
            "channel_url": meta["channelUrl"],
            "latest_videos": videos
        })

    except Exception as e:
        logger.error(f"/channel-about parse error: {e}")
        raise HTTPException(500, "structure changed")


