import logging
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
import asyncio
from yt_dlp import YoutubeDL
import config

logger = logging.getLogger("routers.download_handler")
router = APIRouter()

DOWNLOAD_DIR = Path("./downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)

def _merge_ydl_opts(extra_opts: Optional[dict] = None):
    base_opts = config.YTDLP_OPTIONS.copy()
    if extra_opts:
        base_opts.update(extra_opts)
    # Ensure output template to DOWNLOAD_DIR
    base_opts["outtmpl"] = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")
    return base_opts

def check_format_available(url: str, format_code: str, base_opts: dict) -> bool:
    """
    Check whether the specified 'format_code' is available for the video URL.
    """
    opts = base_opts.copy()
    opts.update({
        "quiet": True,
        "simulate": True,
        "listformats": True,
        "skip_download": True,
    })
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return False
            formats = info.get("formats", [])
            # Check if format_code present among format IDs or format strings
            for f in formats:
                # Some formats may have both 'format_id' and 'format' keys
                if f.get("format_id") == format_code or (format_code in (f.get("format") or "")):
                    return True
            # Also check if format_code is 'bestaudio' or 'best' which are handled specially by yt-dlp
            if format_code in ['best', 'bestaudio']:
                return True
    except Exception as e:
        logger.error(f"Format check failed: {e}", exc_info=True)
        return False
    return False

@router.get("/download")
async def download_video(
    url: str = Query(..., description="YouTube動画URL"),
    format_code: str = Query("best", description=(
        "yt-dlp format code (e.g. 'best', 'bestaudio', '137', '22', 'bestvideo[height<=720]' etc.)"
    )),
    filename: Optional[str] = Query(None, description="保存するファイル名(拡張子含む)を任意で指定可能")
):
    """
    Download video/audio from YouTube using yt-dlp with specified format_code, optionally rename file.
    """
    base_opts = _merge_ydl_opts()

    # Check format availability before download
    available = await asyncio.to_thread(check_format_available, url, format_code, base_opts)
    if not available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"指定されたformat_code '{format_code}' は動画に存在しません。"
                "利用可能なフォーマットを確認し、再度お試しください。"
            )
        )

    # Prepare yt-dlp options for download
    ydl_opts = base_opts.copy()
    ydl_opts["format"] = format_code

    # Handle audio extraction if format_code indicates audio only (e.g. mp3)
    if "mp3" in format_code or format_code == "bestaudio":
        ydl_opts.setdefault("postprocessors", []).append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        })

    def ydldownload():
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise RuntimeError("動画情報の取得に失敗しました。")
                file_path = ydl.prepare_filename(info)
                # yt-dlp may rename to .mp3 when extracting audio
                if ydl_opts.get("postprocessors"):
                    ext = info.get("ext")
                    # If postprocessor changed extension, fix file_path
                    if "ext" in info and info.get("acodec") != "none":
                        # We rely on yt-dlp to rename file after extraction
                        # But file_path might be original extension
                        possible_exts = ['.mp3', '.m4a', '.wav', '.opus']
                        for ext_try in possible_exts:
                            candidate = file_path.rsplit('.',1)[0] + ext_try
                            if Path(candidate).exists():
                                file_path = candidate
                                break
                if not Path(file_path).exists():
                    raise RuntimeError("ダウンロードしたファイルが見つかりません。")
                return file_path, info.get("title", "video")
        except Exception as e:
            logger.error(f"Download error: {e}", exc_info=True)
            raise

    try:
        file_path, title = await asyncio.to_thread(ydldownload)
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(re)
        )
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="動画のダウンロード中に予期しないエラーが発生しました。"
        )

    # Rename if filename specified
    if filename:
        dest_path = DOWNLOAD_DIR / filename
        # Add extension from original file if missing
        if not dest_path.suffix and Path(file_path).suffix:
            dest_path = dest_path.with_suffix(Path(file_path).suffix)
        try:
            shutil.move(file_path, dest_path)
            file_path = str(dest_path)
        except Exception as e:
            logger.warning(f"Failed to rename downloaded file to '{filename}': {e}", exc_info=True)
            # fallback: keep original

    return FileResponse(
        path=file_path,
        filename=Path(file_path).name,
        media_type="application/octet-stream",
        status_code=status.HTTP_200_OK,
    )

@router.get("/download/list")
async def list_downloaded_files():
    """
    Return list of files downloaded with their size info.
    """
    files = []
    for f in sorted(DOWNLOAD_DIR.glob("*")):
        if f.is_file():
            files.append({
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 2)
            })
    return JSONResponse({"count": len(files), "files": files})

@router.delete("/download/delete")
async def delete_downloaded_file(filename: str = Query(..., description="削除したいファイル名")):
    """
    Delete specified downloaded file.
    """
    target = DOWNLOAD_DIR / filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定されたファイルが存在しません。")
    try:
        target.unlink()
        return JSONResponse({"message": f"ファイル '{filename}' を削除しました。"})
    except Exception as e:
        logger.error(f"Failed to delete file '{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ファイルの削除に失敗しました。")
