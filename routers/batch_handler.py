# routers/batch_handler.py
import asyncio, logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query
from yt_dlp import YoutubeDL        # get_stream_infos が内部で使う場合は不要
import config
from routers.extractor_util import get_stream_infos

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(config.ENDPOINTS["batch_extract"])
async def batch_extract(
    urls: str = Query(..., description="カンマ区切り 1–20 件の動画 URL")
) -> Dict[str, List[dict]]:
    """
    与えられた複数 URL を並列で get_stream_infos に掛け、
    { "<url>": [ ...streams... ], ... } を返却する。
    """
    raw_list = [u.strip() for u in urls.split(",") if u.strip()]
    if not raw_list or len(raw_list) > 20:
        raise HTTPException(400, "1–20 URLs required")

    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, get_stream_infos, u) for u in raw_list]

    try:
        results = await asyncio.gather(*tasks)
        return {raw_list[i]: results[i] for i in range(len(raw_list))}
    except Exception as e:
        logger.error(f"/batch-extract error: {e}")
        raise HTTPException(500, "batch extract failed")
