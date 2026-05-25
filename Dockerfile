# ── Node.js + Python 통합 이미지 ──────────────────────────────────────
FROM node:20-slim

# Python3 설치 (Debian Bookworm 기반)
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY skills/requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app

# ── 서버 의존성 설치 ────────────────────────────────────────────────────
COPY web/server/package*.json ./web/server/
RUN cd web/server && npm ci --omit=dev

# ── 클라이언트 빌드 ────────────────────────────────────────────────────
COPY web/client/package*.json ./web/client/
RUN cd web/client && npm ci

COPY web/client/ ./web/client/

# Kakao 지도 키는 빌드 시 주입 (Railway 환경변수 → build arg)
ARG VITE_KAKAO_MAP_KEY
RUN cd web/client && VITE_KAKAO_MAP_KEY=${VITE_KAKAO_MAP_KEY} npm run build

# ── 서버 + 스킬 소스 복사 ───────────────────────────────────────────────
COPY web/server/ ./web/server/
COPY skills/ ./skills/

# 데이터 · 업로드 디렉토리 초기화
RUN mkdir -p web/server/uploads/proof web/server/data

EXPOSE 4000
CMD ["node", "web/server/src/index.js"]
