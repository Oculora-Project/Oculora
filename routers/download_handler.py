import os
import asyncio
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse

import yt_dlp

router = APIRouter()

DOWNLOAD_DIR = Path("./downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ダウンロード管理用メモリ(シンプル実装)
download_tasks = {}  # {url: asyncio.Task}
download_files = {}  # {url: filepath}


async def ytdl_download(url: str) -> Path:
    """
    yt-dlp で指定URLを非同期でダウンロードし、
    ダウンロードファイルパスを返す。
    """
    ydl_opts = {
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    def run_sync():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)
            return Path(filename)

    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(None, run_sync)
    return path


@router.get("/download")
async def download_video(url: str = Query(..., description="YouTube動画URL")):
    """
    ダウンロードリクエスト。既にダウンロード中・済なら状態返す。
    """
    if url in download_files:
        return {"status": "completed", "file": str(download_files[url].name)}

    if url in download_tasks:
        return {"status": "downloading"}

    task = asyncio.create_task(ytdl_download(url))

    download_tasks[url] = task

    def _done_callback(task: asyncio.Task):
        try:
            filepath = task.result()
            download_files[url] = filepath
        except Exception as e:
            # エラー処理。必要ならログ追加
            if url in download_files:
                del download_files[url]
        finally:
            download_tasks.pop(url, None)

    task.add_done_callback(_done_callback)

    return {"status": "download_started"}


@router.get("/files")
async def list_files():
    """
    ダウンロード済みファイルの一覧を返す
    """
    return {"files": [str(f.name) for f in DOWNLOAD_DIR.glob("*")]}


@router.get("/files/{filename}")
async def get_file(filename: str):
    """
    指定ファイルのコンテンツを返す (ストリーミングできる)
    """
    filepath = DOWNLOAD_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(404, "file not found")

    return FileResponse(path=filepath, filename=filename, media_type="application/octet-stream")
