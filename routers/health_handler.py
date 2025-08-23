# routers/health_handler.py
import time, datetime, platform, importlib.metadata as meta
from typing import Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import config

try:
    import psutil
except ImportError:
    psutil = None

router = APIRouter()
START_TIME = time.time()

def _process_info() -> Dict[str, Any]:
    if not psutil:
        return {}
    p = psutil.Process()
    return {
        "pid": p.pid,
        "cpu_percent": p.cpu_percent(interval=None),
        "memory_mb": round(p.memory_info().rss / 1024 / 1024, 2),
        "threads": p.num_threads(),
    }

def _insecure_flags() -> list[str]:
    flags = ("legacy_server_connect", "no_check_certificates", "prefer_insecure")
    return [f for f in flags if config.YTDLP_EXTRA.get(f)]

@router.get(config.ENDPOINTS["health"])
def health_check():
    backend_obj = getattr(config, "CACHE_SETTINGS", {}).get("backend")
    # クラス → 文字列変換
    if backend_obj is None:
        backend = None
    elif isinstance(backend_obj, str):
        backend = backend_obj
    else:
        backend = backend_obj.__name__

    payload = {
        "status": "healthy",
        "service": "video-stream-proxy",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "uptime_sec": int(time.time() - START_TIME),
        "versions": {
            "python": platform.python_version(),
            "fastapi": meta.version("fastapi"),
            "yt_dlp":  meta.version("yt-dlp"),
            "service": getattr(config, "SERVICE_VERSION", "dev"),
        },
        "process": _process_info(),
        "insecure_flags": _insecure_flags(),
        "cache_backend": backend,
    }

    # jsonable_encoder で全てシリアライズ可能な型に変換
    return JSONResponse(content=jsonable_encoder(payload))
