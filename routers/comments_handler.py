import os
import time
import logging
from typing import Dict, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from threading import Lock

router = APIRouter()
logger = logging.getLogger(__name__)

YOUTUBE_URL_TEMPLATE = "https://www.youtube.com/watch?v={}"

# ── キャッシュ構造 ─────────────
_comments_cache: Dict[str, Dict] = {}
_cache_lock = Lock()
_CACHE_TTL = 60 * 5  # 5分キャッシュ


def get_cached_comments(video_id: str):
    with _cache_lock:
        entry = _comments_cache.get(video_id)
        if entry:
            if time.time() - entry["time"] < _CACHE_TTL:
                return entry["data"]
            else:
                # 古いキャッシュを削除
                del _comments_cache[video_id]
    return None


def set_cached_comments(video_id: str, data):
    with _cache_lock:
        _comments_cache[video_id] = {"time": time.time(), "data": data}


@router.get("/comments")
def get_youtube_comments(v: str = Query(..., description="YouTube動画ID")):
    if not v or len(v) < 5:
        raise HTTPException(400, "invalid video id")
    video_id = v.strip()

    # キャッシュ確認
    cached = get_cached_comments(video_id)
    if cached is not None:
        logger.info(f"[cache hit] /comments?video_id={video_id}")
        return JSONResponse(content=cached)

    url = YOUTUBE_URL_TEMPLATE.format(video_id)

    options = webdriver.ChromeOptions()
    options.add_argument("--lang=ja-JP")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        # Selenium Stealth セットアップ
        stealth(driver,
                languages=["ja-JP", "en-US"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

        driver.set_window_size(1280, 800)
        driver.get(url)

        # コメントセクション読み込み待ち
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
            )
        except Exception:
            driver.quit()
            logger.info("コメントセクションが読み込めませんでした")
            raise HTTPException(502, "failed to load comments")

        # 最大限スクロールしてコメント取得
        prev_count = 0
        for _ in range(12):  # 状況に合わせて回数調整可
            driver.execute_script("window.scrollBy(0, 4000);")
            time.sleep(2)
            comment_threads = driver.find_elements(By.XPATH, '//*[@id="contents"]/ytd-comment-thread-renderer')
            curr_count = len(comment_threads)
            if curr_count == prev_count:
                break
            prev_count = curr_count

        results: List[Dict] = []

        for thread in comment_threads:
            try:
                main_comment = thread.find_element(By.ID, "comment")
                username = main_comment.find_element(By.ID, "author-text").text.strip()
                avatar = main_comment.find_element(By.XPATH, './/img[@id="img"]').get_attribute("src")
                text = main_comment.find_element(By.ID, "content-text").text.strip()
                results.append({
                    "user": username if username else "",
                    "icon": avatar,
                    "comment": text,
                    "is_reply": False,
                })
                replies = thread.find_elements(By.XPATH, './/ytd-comment-replies-renderer//ytd-comment-renderer')
                for reply in replies:
                    reply_user = reply.find_element(By.ID, "author-text").text.strip()
                    reply_avatar = reply.find_element(By.XPATH, './/img[@id="img"]').get_attribute("src")
                    reply_text = reply.find_element(By.ID, "content-text").text.strip()
                    results.append({
                        "user": reply_user if reply_user else "",
                        "icon": reply_avatar,
                        "comment": reply_text,
                        "is_reply": True,
                    })
            except Exception:
                continue  # エラーはスキップ

        driver.quit()

        # キャッシュ保存
        set_cached_comments(video_id, results)

        return JSONResponse(content=results)

    except Exception as e:
        logger.error(f"/comments error: {e}")
        raise HTTPException(500, "comments extraction failed")
