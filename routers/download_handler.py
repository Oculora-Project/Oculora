from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
from pathlib import Path
import shutil

router = APIRouter()

DOWNLOAD_DIR = Path("./downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

@router.get("/download")
def download_video(
    url: str = Query(..., description="YouTube動画URL"),
    format_code: str = Query(None, description="yt-dlpフォーマットコード。例：'best', 'bestaudio', 'bestvideo[height<=720]'"),
    filename: str = Query(None, description="保存ファイル名。拡張子含む（指定なければ自動決定）")
):
    """
    YouTube動画ダウンロードAPI。
    format_codeで画質・フォーマット指定（例：mp3ならbestaudio+音声変換が自動でできる）
    filenameを指定するとその名前で保存。指定無ければyt-dlpのデフォルト名。
    """
    ydl_opts = {
        "format": format_code or "best",
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "postprocessors": []
    }

    # mp3対応例: format_codeにaudio系指定なら変換追加も可能
    if format_code and ("mp3" in format_code or "bestaudio" in format_code):
        ydl_opts["postprocessors"].append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",  # 音質ビットレート
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            out_file = ydl.prepare_filename(info)
            # ファイル名カスタム対応
            if filename:
                ext = Path(out_file).suffix
                new_path = DOWNLOAD_DIR / filename
                if not new_path.suffix:
                    new_path = new_path.with_suffix(ext)
                shutil.move(out_file, new_path)
                out_file = str(new_path)

            return FileResponse(out_file, media_type="application/octet-stream", filename=Path(out_file).name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")



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
