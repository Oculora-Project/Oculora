import logging
import shutil
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
import asyncio
from yt_dlp import YoutubeDL

logger = logging.getLogger("routers.download_handler")
router = APIRouter()

DOWNLOAD_DIR = Path("./downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)

@router.get("/download")
async def download_video(
    url: str = Query(..., description="YouTube動画URL"),
    format_code: str = Query("best", description="yt-dlp用フォーマット指定例: 'best', 'bestaudio', 'bestvideo[height<=720]'"),
    filename: str = Query(None, description="保存ファイル名（拡張子含む、省略可）")
):
    """
    指定URLの動画を指定フォーマットでダウンロードし返却。  
    ファイル名指定可能。音声（mp3等）もformat_code次第で対応。
    """
    def run_ydl_sync():
        postprocessors = []
        # mp3変換対応例
        if format_code and ("mp3" in format_code or format_code == "bestaudio"):
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            })
        opts = {
            "format": format_code,
            "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
            "quiet": True,
            "ignoreerrors": True,
            "postprocessors": postprocessors,
        }

        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise RuntimeError("間違ったURLか動画情報が取得できません")
            # 対応フォーマットが無い場合に備え例外もキャッチしたい
            if info.get('requested_formats') is not None:
                # フォーマット不正は別例外で出るためここはスキップ可
                pass
            out_file = ydl.prepare_filename(info)
            return out_file, info.get("title", "video")

    try:
        out_file, title = await asyncio.to_thread(run_ydl_sync)
    except RuntimeError as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Download failed unexpected error", exc_info=True)
        raise HTTPException(status_code=500, detail="動画のダウンロードに失敗しました。format_code指定やURLを確認してください。")

    if filename:
        try:
            new_path = DOWNLOAD_DIR / filename
            # 拡張子がなければ元ファイルのものを付与
            if not new_path.suffix:
                new_path = new_path.with_suffix(Path(out_file).suffix)
            shutil.move(out_file, new_path)
            out_file = str(new_path)
        except Exception as e:
            logger.error(f"ファイル名変更失敗: {e}", exc_info=True)
            # 変更失敗は警告で続行

    return FileResponse(
        path=out_file,
        media_type="application/octet-stream",
        filename=Path(out_file).name,
        status_code=status.HTTP_200_OK
    )

@router.get("/download/list")
async def list_downloaded_files():
    """
    ダウンロード済ファイルの一覧取得API
    """
    files = []
    for file in sorted(DOWNLOAD_DIR.glob("*")):
        if file.is_file():
            files.append({"name": file.name, "size_kb": round(file.stat().st_size / 1024, 2)})
    return JSONResponse(content={"count": len(files), "files": files})

@router.delete("/download/delete")
async def delete_downloaded_file(
    filename: str = Query(..., description="削除したいファイル名（必須）")
):
    """
    指定したファイル名のファイルを削除するAPI
    """
    file_path = DOWNLOAD_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="指定ファイルは存在しません")
    try:
        file_path.unlink()
        return JSONResponse(content={"message": f"{filename} を削除しました"})
    except Exception as e:
        logger.error(f"ファイル削除エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ファイル削除処理に失敗しました")

