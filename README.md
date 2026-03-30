# Personal Backoffice

콘텐츠 자동화 + 자동매매 + 가계부 대시보드

## 구조

```
web/          → Next.js 대시보드 (Vercel)
worker/       → Cloud Run 워커 (Python)
*.py          → CLI 도구 (로컬)
```

## 로컬 개발 환경 설정

### 필수 설치

```bash
# Python 의존성
pip install -r requirements.txt

# Node.js 의존성
cd web && npm install

# FFmpeg (영상 조립용)
# Windows: https://www.gyan.dev/ffmpeg/builds/ 에서 다운로드
#   → ffmpeg-release-essentials.zip 다운로드
#   → 압축 해제 → bin 폴더를 시스템 PATH에 추가
#   → 또는: winget install ffmpeg
#
# Mac: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

### 환경변수

```bash
# 루트 .env (Python CLI용)
GEMINI_API_KEY=
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEETS_ID=
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_ACCOUNT_NO=
KIS_POSITIONS_BUCKET=

# web/.env.local (Next.js용)
# web/.env.example 참고
```

## 서버 실행

```bash
# Next.js 개발 서버
cd web && npm run dev

# 프로덕션 빌드
cd web && npm run build && npm start
```

## CLI 명령어

```bash
# 구글 시트 초기화
python main.py init-sheets

# 블로그 키워드 추천
python main.py blog dev
python main.py blog cpc

# 블로그 초안 생성
python main.py blog dev "키워드"
python main.py blog cpc "청년 도약계좌" --cpc-category "청년 지원금"

# 매일 자동 초안 생성 (dev + cpc)
python main.py daily

# 매매 데이터 동기화
python sync_trading.py

# 릴스 분석 + 콘티 생성
python main.py url "영상URL" --story "내 썰"
python main.py batch "URL1" "URL2" "URL3"
```

## 배포

- **Vercel**: `web/` 디렉토리, Root Directory = `web`
- **Cloud Run**: `worker/` 디렉토리
- **Cloud Scheduler**: 매일 07:00 블로그 초안, 평일 15:40 매매 동기화
