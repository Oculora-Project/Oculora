import logging
import uvicorn
import config      # すべての設定をここで読む

logger = logging.getLogger(__name__)

def main() -> None:
    logger.info("=" * 55)
    logger.info("Oculora API Starting...")
    logger.info("Host: %s", config.HOST)
    logger.info("Port: %s", config.PORT)
    logger.info("Reload: %s", config.DEBUG)
    logger.info("Workers: %s", config.WORKERS)
    logger.info("Log Level: %s", config.LOG_LEVEL)
    logger.info("=" * 55)

    # ────────────────────────────────────────────────
    # ① 文字列 "main:app" を渡す
    #    main … FastAPI を定義したモジュール名 (main.py)
    #    app  … そのモジュール内の変数名
    # ────────────────────────────────────────────────
    uvicorn.run(
        "server:app",                 # ← ここを文字列に
        host     = config.HOST,
        port     = config.PORT,
        reload   = config.DEBUG,    # DEBUG=True なら自動リロード
        workers  = config.WORKERS,  # 2 以上可
        log_level= config.LOG_LEVEL.lower(),
    )

if __name__ == "__main__":
    main()
