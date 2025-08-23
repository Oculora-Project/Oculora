import re
import asyncio
import logging
from urllib.parse import urljoin, quote

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
from aiocache import Cache, SimpleMemoryCache

import config

logger = logging.getLogger(__name__)

# ───────────────── 共通設定 ─────────────────
URI_RE = re.compile(config.REGEX_PATTERNS["uri_pattern"])
router = APIRouter()

# ───────────────── 内部 util ─────────────────
async def _http_get(url: str, headers: dict):
    async with httpx.AsyncClient(http2=True, timeout=config.HTTP_SETTINGS["timeout"]) as client:
        return await client.get(url, headers=headers, follow_redirects=True)

def _cache_key(url: str) -> str:
    return f"{config.CACHE_SETTINGS['namespace']}:{url}"

def _cache_key_m3u8(url: str) -> str:
    return f"{config.CACHE_SETTINGS['namespace']}:rewritten:{url}"

async def fetch_with_retry(url: str, headers: dict, retries: int = None):
    retries = retries if retries is not None else config.HTTP_SETTINGS["retries"]
    for attempt in range(retries + 1):
        try:
            r = await _http_get(url, headers)
            if r.status_code >= 400:
                raise HTTPException(r.status_code, f"Upstream returned {r.status_code}")
            return r
        except httpx.TimeoutException:
            if attempt == retries:
                raise HTTPException(408, config.RESPONSE_SETTINGS["error_messages"]["timeout_error"])
            logger.warning(f"Timeout {attempt+1}/{retries} → retry: {url}")
            await asyncio.sleep(1)

def rewrite_m3u8(text: str, base_url: str, proxy_base: str) -> str:
    """m3u8 内の URL / KEY URI をプロキシ付きに書き換え + EXT-X-START 追加"""
    out = []

    # 冒頭に EXT-X-START を挿入（存在しない場合のみ）
    if "#EXT-X-START" not in text:
        out.append("#EXT-X-START:TIME-OFFSET=0,PRECISE=YES")

    def proxify(u: str) -> str:
        full = urljoin(base_url, u)
        return proxy_base + quote(full, safe=config.PROXY_SETTINGS["url_safe_chars"])

    for line in text.splitlines():
        if line.startswith("#"):
            line = URI_RE.sub(lambda m: f'URI="{proxify(m.group(1))}"', line)
            out.append(line)
        elif line.strip():
            out.append(proxify(line.strip()))
        else:
            out.append(line)
    return "\n".join(out)

# ───────────────── TS 先読み + メモリキャッシュ ─────────────────
ts_memory_cache = {}  # {url: bytes}

async def stream_ts_cached(urls: list, headers: dict,
                           init_chunk: int = 128*1024,
                           max_chunk: int = 256*1024,
                           prefetch_segments: int = 3):
    """
    複数TSセグメントを同時に先読みしてバッファリング
    urls: TS URL のリスト
    """
    queue = asyncio.Queue(maxsize=prefetch_segments)
    data_buffer = bytearray()

    async def fetch_segment(seg_url: str):
        nonlocal queue, data_buffer
        if seg_url in ts_memory_cache:
            await queue.put(ts_memory_cache[seg_url])
            return
        async with httpx.AsyncClient(http2=True, timeout=None) as client:
            async with client.stream("GET", seg_url, headers=headers) as r:
                if r.status_code >= 400:
                    await queue.put(HTTPException(r.status_code, f"Upstream returned {r.status_code}"))
                    return
                chunk_size = init_chunk
                async for chunk in r.aiter_bytes(chunk_size=chunk_size):
                    await queue.put(chunk)
                    data_buffer.extend(chunk)
        ts_memory_cache[seg_url] = bytes(data_buffer)

    async def producer():
        tasks = []
        for i, seg_url in enumerate(urls[:prefetch_segments]):
            tasks.append(asyncio.create_task(fetch_segment(seg_url)))
        await asyncio.gather(*tasks)
        # それ以降は順次取得
        for seg_url in urls[prefetch_segments:]:
            await fetch_segment(seg_url)
        await queue.put(None)

    async def consumer():
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                if isinstance(chunk, Exception):
                    raise chunk
                yield chunk
        finally:
            if not producer_task.done():
                producer_task.cancel()

    producer_task = asyncio.create_task(producer())
    async for data in consumer():
        yield data

# ───────────────── /proxy エンドポイント ─────────────────
@router.get(config.ENDPOINTS["proxy"])
async def proxy(url: str, request: Request):
    logger.debug(f"Proxy request: {url}")
    try:
        m3u8_mark = config.STREAM_EXTRACTION["m3u8_check_string"]
        is_m3u8 = url.endswith(m3u8_mark)
        headers = {}
        if "range" in request.headers:
            headers["Range"] = request.headers["range"]

        # ---------- m3u8 ----------
        m3u8_mt = config.RESPONSE_SETTINGS["m3u8_media_type"]
        if is_m3u8:
            cache = Cache(SimpleMemoryCache)
            cache_key = _cache_key_m3u8(url)
            cached_txt = await cache.get(cache_key)
            if cached_txt is None:
                r = await fetch_with_retry(url, headers)
                base_url = str(request.base_url).rstrip('/')
                proxy_base = f"{base_url}/{config.PROXY_SETTINGS['base_path']}"
                body = rewrite_m3u8(r.text, url, proxy_base)
                await cache.set(cache_key, body, ttl=config.CACHE_SETTINGS["ttl_m3u8"])
                logger.debug(f"m3u8 cached: {url}")
            else:
                body = cached_txt
                logger.debug(f"m3u8 cache hit: {url}")
            return Response(
                body,
                media_type=m3u8_mt,
                headers={"Cache-Control": f"public, max-age={config.CACHE_SETTINGS['ttl_m3u8']}"}
            )

        # ---------- TS / KEY / その他 ----------
        # 単一TSの場合もリスト化
        ts_urls = [url] if url.endswith(".ts") else [url]
        return StreamingResponse(
            stream_ts_cached(ts_urls, headers, init_chunk=config.PROXY_SETTINGS["buffer_size"]),
            media_type="application/octet-stream",
            headers={"Cache-Control": f"public, max-age={config.CACHE_SETTINGS['ttl_segment']}"},
        )

    except Exception as e:
        logger.error(f"Proxy error: {type(e).__name__}: {e}")
        raise HTTPException(
            500,
            config.RESPONSE_SETTINGS["error_messages"]["upstream_error"],
        )

cache = Cache(SimpleMemoryCache)
