import logging
from typing import Any, Dict
from yt_dlp import YoutubeDL
import config

logger = logging.getLogger(__name__)

_SEC_WARN = (
    "⚠ You have enabled --legacy-server-connect / "
    "--no-check-certificates / --prefer-insecure. "
    "These options weaken HTTPS security."
)

def _merge_opts() -> Dict[str, Any]:
    base = config.YTDLP_OPTIONS.copy()
    extra = getattr(config, "YTDLP_EXTRA", {})

    # proxy
    if extra.get("proxy"):
        base["proxy"] = extra["proxy"]

    # insecure flags
    if any(extra.get(k) for k in ("legacy_server_connect", "no_check_certificates", "prefer_insecure")):
        logger.warning(_SEC_WARN)
    if extra.get("legacy_server_connect"):
        base["legacy_server_connect"] = True
    if extra.get("no_check_certificates"):
        base["nocheckcertificate"] = True
    if extra.get("prefer_insecure"):
        base["prefer_insecure"] = True

    # external downloader
    edl, eargs = extra.get("external_downloader"), extra.get("external_downloader_args")
    if edl and eargs:
        base["external_downloader"] = edl
        base["external_downloader_args"] = eargs
    else:
        base.pop("external_downloader", None)
        base.pop("external_downloader_args", None)

    return base

def run_ydl(url: str, custom: Dict[str, Any] | None = None):
    opts = _merge_opts()
    if custom:
        opts |= custom
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)
