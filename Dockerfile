# Dockerfile
FROM python:3.11-slim

# システム依存のインストール（ChromeとXvfbの準備）
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg2 \
    unzip \
    ca-certificates \
    fonts-liberation \
    libx11-xcb1 \
    libxss1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libatk1.0-0 \
    libgbm1 \
    libasound2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Google Chromeインストール
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install && \
    rm google-chrome-stable_current_amd64.deb

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ENV設定
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

EXPOSE 8000

CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 & uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1"]
