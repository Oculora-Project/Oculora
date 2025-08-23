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
    channel_url: str = Query(..., description="https://www.youtube.com/@<handle>")
):
    if not re.match(r"^https://(www\.)?youtube\.com/@.+", channel_url):
        raise HTTPException(400, "invalid channel url")

    data = await _fetch_initial_data(channel_url + "/about")
    try:
        meta = data["metadata"]["channelMetadataRenderer"]
        return JSONResponse({
            "title":       meta["title"],
            "description": meta.get("description"),
            "subscriber":  meta.get("subscriberCountText", {}).get("simpleText"),
            "avatar":      meta["avatar"]["thumbnails"][-1]["url"],
            "channel_url": meta["channelUrl"]
        })
    except Exception as e:
        logger.error(f"/channel-about parse error: {e}")
        raise HTTPException(500, "structure changed")
