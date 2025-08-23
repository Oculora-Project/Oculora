# extractor.py

from yt_dlp import YoutubeDL
import config
import logging

# ログ設定
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=config.LOGGING_SETTINGS["level"],
    format=config.LOGGING_SETTINGS["format"]
)

def get_stream_infos(page_url: str) -> list[dict]:
    """
    戻り値:
        [
          {
            "type": "video" | "audio",
            "quality": "1080p" / "720p" / "144p" / "audio-128k" …,
            "url": "https://…m3u8"
          },
          …
        ]
    """
    logger.info(f"Extracting stream info from: {page_url}")
    
    # 設定から yt-dlp オプションを取得
    ydl_opts = config.YTDLP_OPTIONS.copy()
    
    streams: list[dict] = []

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)

            if not info:
                logger.error("Failed to extract info from URL")
                return streams

            formats = info.get("formats", [])
            logger.debug(f"Found {len(formats)} formats")

            for f in formats:
                # m3u8 が絡むフォーマットのみ
                supported_protocols = config.STREAM_EXTRACTION["supported_protocols"]
                m3u8_check = config.STREAM_EXTRACTION["m3u8_check_string"]
                
                protocol_check = f.get("protocol") not in supported_protocols
                url_check = m3u8_check not in (f.get("url") or "")
                
                if protocol_check and url_check:
                    continue

                # 種別判定
                video_codec_none = config.STREAM_EXTRACTION["video_codec_none"]
                stream_type = "audio" if f.get("vcodec") == video_codec_none else "video"

                # 画質／音質ラベル
                if stream_type == "video":
                    # 例: 1920x1080 → 1080p
                    unknown_label = config.STREAM_EXTRACTION["unknown_height_label"]
                    res = f.get("resolution") or f"{f.get('height', unknown_label)}p"
                    quality = res
                else:
                    # 例: 128k, 50k …
                    abr = f.get("abr")
                    prefix = config.STREAM_EXTRACTION["audio_quality_prefix"]
                    quality = f"{prefix}-{int(abr)}k" if abr else prefix

                # m3u8 URL は url / manifest_url のどちらかにある
                m3u8_url = f.get("manifest_url") or f.get("url")
                if not m3u8_url:
                    continue

                streams.append({
                    "type": stream_type, 
                    "quality": quality, 
                    "url": m3u8_url
                })

                # 最大ストリーム数制限
                max_streams = config.STREAM_EXTRACTION["max_streams"]
                if len(streams) >= max_streams:
                    logger.warning(f"Reached maximum stream limit ({max_streams})")
                    break

            # YouTube ライブ等、info["url"] 自体が m3u8 のケース
            top_url = info.get("url")
            if isinstance(top_url, str) and m3u8_check in top_url:
                default_quality = config.STREAM_EXTRACTION["default_video_quality"]
                streams.append({
                    "type": "video", 
                    "quality": default_quality, 
                    "url": top_url
                })

            logger.info(f"Extracted {len(streams)} streams")
            
    except Exception as e:
        logger.error(f"Error extracting streams: {str(e)}")
        
    return streams