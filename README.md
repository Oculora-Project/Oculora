# Oculora
**Oculora Project** は、YouTubeの動画・プレイリスト・チャンネル・コメント情報の取得、HLSストリームのプロキシ配信を行う API サーバーです。 `FastAPI`＋`yt-dlp`を中心に構成され、Seleniumによるコメント取得も対応しています。

---
## 特徴 
- YouTube動画/プレイリスト情報のREST API提供 
- HLS (.m3u8)ストリーム/TSセグメントのプロキシ
- 関連動画・検索・チャンネルメタ情報取得 
- コメント抽出（Selenium＋Stealthで突破） 
- キャッシュによる高速化 
- .env＆config.py経由で環境変数による柔軟設定 
---

##  ディレクトリ構成例
```
project_root/  
├── server.py  
├── run.py  
├── requirements.txt  
├── .env  
├── .gitignore  
├── README.md  
├── config/  
│ ├── **init**.py  
│ └── config.py  
└── routers/  
├── proxy_handler.py  
├── batch_handler.py  
├── playlist_handler.py  
├── channel_handler.py  
├── related_handler.py  
├── transcode_handler.py  
├── stream_direct_handler.py  
├── extract_handler.py  
├── health_handler.py  
├── comments_handler.py  
├── search_handler.py  
└── extractor_util.py
```
---
##  インストール ### 1. 必要パッケージのインストール
```bash
pip install -r requirements.txt
```
### 2. .envファイルの用意 サンプル（必要な項目のみ）:
```bash
HOST=0.0.0.0  
PORT=8000  
DEBUG=True  
WORKERS=1  
LOG_LEVEL=INFO
```
### 3. ChromeDriver/Selenium準備 `webdriver-manager`利用で自動ダウンロードされます。 
- ##  起動方法 (開発用)
```bash
python run.py
```
- `server.py`または`main.py`がFastAPIエントリポイントです。

---

##  主なAPIエンドポイント

| エンドポイント           | 説明                          | メソッド | 必須パラメータ             |
|-------------------------|-------------------------------|----------|----------------------------|
| `/extract`              | 動画メタ＋ストリーム一覧      | GET      | url                        |
| `/proxy`                | m3u8/TSプロキシ配信           | GET      | url                        |
| `/stream-direct`        | 単一動画のm3u8URL取得         | GET      | video_url                  |
| `/transcode`            | MP4変換ストリーム取得         | GET      | video_url                  |
| `/search`               | YouTube検索                   | GET      | q, limit                   |
| `/related-videos`       | 関連動画取得                  | GET      | url, limit                 |
| `/comments`             | コメント抽出                  | GET      | v (動画ID)                 |
| `/health`               | サーバーヘルス/環境確認       | GET      | なし                       |
| `/channel-about`        | チャンネル情報取得            | GET      | channel_url                |
| `/playlist-info`        | プレイリスト一覧メタ取得       | GET      | playlist_url               |
| `/batch-extract`        | 複数動画ストリーム一括取得     | GET      | urls (カンマ区切り)        |

---

## 詳細なAPIエンドポイント
```bash
https://localhost:8080/docs
```

---

## 開発・カスタマイズ

- 設定は `.env` と `config/config.py` で行います。
  - **APIキー・トークン・環境依存値は必ず.envで管理してください。**
- 各API分岐は `routers/` 配下に整理されています。

---

##  依存関係

- fastapi
- uvicorn
- httpx
- yt-dlp
- aiocache
- selenium
- webdriver-manager
- selenium-stealth
- psutil
- python-dotenv

---

##  ライセンス & 注意点

- YouTube規約や動画配信に伴う著作権・利用規約を必ず遵守してください。
- 本コードは教育／研究／検証目的の参考実装です。

---

##  貢献/バグ報告/要望

- [bug_report.md](./bug_report.md) を参考にバグ報告
- [feature_request.md](./feature_request.md) に新機能要望
- プルリク/Issue歓迎


