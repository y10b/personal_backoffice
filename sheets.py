"""구글 시트 연동 모듈.

사전 준비:
1. Google Cloud Console에서 프로젝트 생성
2. Google Sheets API + Google Drive API 활성화
3. 서비스 계정 생성 → JSON 키 다운로드
4. .env에 추가:
   GOOGLE_SHEETS_CREDENTIALS=credentials.json  (키 파일 경로)
   GOOGLE_SHEETS_ID=스프레드시트_ID
5. 스프레드시트를 서비스 계정 이메일에 편집 권한 공유

시트 구조 (자동 생성됨):
  [대시보드] - 요약 통계
  [블로그-초안] - 생성된 초안 목록
  [블로그-발행] - 발행 완료 목록
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from models import BlogPost

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# 시트 컬럼 정의
DRAFT_HEADERS = [
    "ID", "날짜", "시간", "블로그타입", "CPC카테고리",
    "제목", "키워드", "슬러그", "카테고리", "태그",
    "메타디스크립션", "읽기시간(분)", "상태",
    "HTML본문", "이미지프롬프트", "수정메모",
]

PUBLISH_HEADERS = [
    "ID", "초안ID", "발행일시", "블로그타입", "블로그이름",
    "제목", "키워드", "티스토리PostID", "URL",
]

CONTI_REQUEST_HEADERS = [
    "ID", "날짜", "시간", "타입", "URL", "썰", "콘텐츠유형", "상태",
    # 타입: url / story
    # 상태: 대기 / 처리중 / 완료 / 실패
]

CONTI_HEADERS = [
    "ID", "날짜", "시간", "제목", "유형", "총길이(초)",
    "상태", "원본URL", "콘티JSON", "메모",
    # 유형: 알바 썰 / 개발 자랑 / 학습 공유 / 과거 썰
    # 상태: 초안 / 촬영중 / 편집중 / 발행완료
]

THREADS_HEADERS = [
    "ID", "날짜", "원본타입", "원본ID", "내용", "상태",
    # 원본타입: 블로그 / 릴스
    # 상태: 초안 / 발행완료
]

KEYWORD_HEADERS = [
    "날짜", "키워드", "블로그타입", "글ID", "구글순위", "네이버순위",
]

BUDGET_SETTINGS_HEADERS = [
    "항목", "타입", "금액", "메모",
    # 타입: 수입/고정지출/저축비율
    # 예: 월급, 수입, 2500000, 롯데리아
    # 예: 월세, 고정지출, 500000, 매달 25일
    # 예: 저축, 저축비율, 30, 퍼센트
]

EXPENSE_HEADERS = [
    "날짜", "카테고리", "항목", "금액", "메모",
    # 카테고리: 식비/교통/문화/쇼핑/기타
]

BALANCE_HEADERS = [
    "날짜", "시간", "총평가금액", "매입금액", "미실현손익",
    "예수금", "보유종목수",
]

HOLDINGS_HEADERS = [
    "날짜", "종목코드", "종목명", "수량", "매수가", "현재가",
    "수익률(%)", "손익", "손절가", "목표가", "매수일",
]

TRADE_HISTORY_HEADERS = [
    "날짜", "종목코드", "종목명", "수익률(%)", "손익",
]


def _get_client() -> gspread.Client:
    cred_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
    creds = Credentials.from_service_account_file(cred_path, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_spreadsheet() -> gspread.Spreadsheet:
    client = _get_client()
    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
    if not sheet_id:
        raise RuntimeError(
            ".env에 GOOGLE_SHEETS_ID를 설정해주세요.\n"
            "구글 스프레드시트 URL에서 /d/여기가_ID/edit 부분입니다."
        )
    return client.open_by_key(sheet_id)


def init_sheets():
    """시트 초기화 — 없는 시트 생성 + 헤더 세팅."""
    ss = _get_spreadsheet()
    existing = [ws.title for ws in ss.worksheets()]

    if "블로그-초안" not in existing:
        ws = ss.add_worksheet("블로그-초안", rows=1000, cols=len(DRAFT_HEADERS))
        ws.append_row(DRAFT_HEADERS)
        print("  ✓ '블로그-초안' 시트 생성")

    if "블로그-발행" not in existing:
        ws = ss.add_worksheet("블로그-발행", rows=1000, cols=len(PUBLISH_HEADERS))
        ws.append_row(PUBLISH_HEADERS)
        print("  ✓ '블로그-발행' 시트 생성")

    if "매매-잔고" not in existing:
        ws = ss.add_worksheet("매매-잔고", rows=1000, cols=len(BALANCE_HEADERS))
        ws.append_row(BALANCE_HEADERS)
        print("  ✓ '매매-잔고' 시트 생성")

    if "매매-보유종목" not in existing:
        ws = ss.add_worksheet("매매-보유종목", rows=1000, cols=len(HOLDINGS_HEADERS))
        ws.append_row(HOLDINGS_HEADERS)
        print("  ✓ '매매-보유종목' 시트 생성")

    if "매매-이력" not in existing:
        ws = ss.add_worksheet("매매-이력", rows=1000, cols=len(TRADE_HISTORY_HEADERS))
        ws.append_row(TRADE_HISTORY_HEADERS)
        print("  ✓ '매매-이력' 시트 생성")

    if "릴스-요청" not in existing:
        ws = ss.add_worksheet("릴스-요청", rows=1000, cols=len(CONTI_REQUEST_HEADERS))
        ws.append_row(CONTI_REQUEST_HEADERS)
        print("  ✓ '릴스-요청' 시트 생성")

    if "릴스-콘티" not in existing:
        ws = ss.add_worksheet("릴스-콘티", rows=1000, cols=len(CONTI_HEADERS))
        ws.append_row(CONTI_HEADERS)
        print("  ✓ '릴스-콘티' 시트 생성")

    if "쓰레드" not in existing:
        ws = ss.add_worksheet("쓰레드", rows=1000, cols=len(THREADS_HEADERS))
        ws.append_row(THREADS_HEADERS)
        print("  ✓ '쓰레드' 시트 생성")

    if "키워드-트래킹" not in existing:
        ws = ss.add_worksheet("키워드-트래킹", rows=5000, cols=len(KEYWORD_HEADERS))
        ws.append_row(KEYWORD_HEADERS)
        print("  ✓ '키워드-트래킹' 시트 생성")

    if "가계부-설정" not in existing:
        ws = ss.add_worksheet("가계부-설정", rows=100, cols=len(BUDGET_SETTINGS_HEADERS))
        ws.append_row(BUDGET_SETTINGS_HEADERS)
        print("  ✓ '가계부-설정' 시트 생성")

    if "가계부-지출" not in existing:
        ws = ss.add_worksheet("가계부-지출", rows=5000, cols=len(EXPENSE_HEADERS))
        ws.append_row(EXPENSE_HEADERS)
        print("  ✓ '가계부-지출' 시트 생성")

    # 기본 Sheet1 삭제 (있으면)
    if "Sheet1" in existing and len(existing) > 1:
        try:
            ss.del_worksheet(ss.worksheet("Sheet1"))
        except Exception:
            pass

    print("  ✓ 구글 시트 초기화 완료")


def _next_id(ws: gspread.Worksheet) -> str:
    """다음 ID 생성 (YYYYMMDD-NNN)."""
    today = datetime.now().strftime("%Y%m%d")
    all_ids = ws.col_values(1)[1:]  # 헤더 제외
    today_ids = [i for i in all_ids if i.startswith(today)]
    seq = len(today_ids) + 1
    return f"{today}-{seq:03d}"


def save_draft(post: BlogPost, blog_type: str) -> str:
    """초안을 구글 시트에 저장한다. 반환: draft ID."""
    ss = _get_spreadsheet()
    ws = ss.worksheet("블로그-초안")

    draft_id = _next_id(ws)
    now = datetime.now()

    images_json = json.dumps(
        [img.model_dump() for img in post.images],
        ensure_ascii=False,
    ) if post.images else ""

    row = [
        draft_id,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M"),
        blog_type,
        post.cpc_category,
        post.title,
        ", ".join(post.keywords),
        post.slug,
        post.category,
        ", ".join(post.tags),
        post.meta_description,
        str(post.estimated_reading_min),
        "초안",  # 상태: 초안 / 리뷰중 / 수정완료 / 발행완료
        post.html_content,
        images_json,
        "",  # 수정 메모
    ]

    ws.append_row(row, value_input_option="RAW")
    return draft_id


def get_drafts(status: str | None = None, date: str | None = None) -> list[dict]:
    """초안 목록 조회. status: 초안/리뷰중/수정완료/발행완료, date: YYYY-MM-DD."""
    ss = _get_spreadsheet()
    ws = ss.worksheet("블로그-초안")
    records = ws.get_all_records()

    if status:
        records = [r for r in records if r.get("상태") == status]
    if date:
        records = [r for r in records if r.get("날짜") == date]

    return records


def get_draft_by_id(draft_id: str) -> dict | None:
    """ID로 초안 조회."""
    ss = _get_spreadsheet()
    ws = ss.worksheet("블로그-초안")
    records = ws.get_all_records()

    for r in records:
        if r.get("ID") == draft_id:
            return r
    return None


def update_draft_status(draft_id: str, status: str, memo: str = ""):
    """초안 상태 업데이트."""
    ss = _get_spreadsheet()
    ws = ss.worksheet("블로그-초안")

    # ID 컬럼에서 행 찾기
    ids = ws.col_values(1)
    try:
        row_idx = ids.index(draft_id) + 1  # 1-indexed
    except ValueError:
        raise RuntimeError(f"초안을 찾을 수 없습니다: {draft_id}")

    # 상태 컬럼 (13번째)
    ws.update_cell(row_idx, 13, status)
    if memo:
        ws.update_cell(row_idx, 16, memo)


def update_draft_content(draft_id: str, html_content: str):
    """초안 HTML 본문 업데이트 (수정 후)."""
    ss = _get_spreadsheet()
    ws = ss.worksheet("블로그-초안")

    ids = ws.col_values(1)
    try:
        row_idx = ids.index(draft_id) + 1
    except ValueError:
        raise RuntimeError(f"초안을 찾을 수 없습니다: {draft_id}")

    ws.update_cell(row_idx, 14, html_content)
    ws.update_cell(row_idx, 13, "수정완료")


def record_publish(draft_id: str, blog_type: str, blog_name: str, title: str,
                   keywords: str, post_id: str, url: str = ""):
    """발행 기록을 저장한다."""
    ss = _get_spreadsheet()
    ws = ss.worksheet("블로그-발행")

    publish_id = _next_id(ws)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    row = [
        publish_id, draft_id, now, blog_type, blog_name,
        title, keywords, post_id, url,
    ]
    ws.append_row(row, value_input_option="RAW")

    # 초안 상태도 업데이트
    update_draft_status(draft_id, "발행완료")

    return publish_id


def get_dashboard_stats() -> dict:
    """대시보드 통계."""
    ss = _get_spreadsheet()
    ws_draft = ss.worksheet("블로그-초안")
    ws_pub = ss.worksheet("블로그-발행")

    drafts = ws_draft.get_all_records()
    publishes = ws_pub.get_all_records()

    today = datetime.now().strftime("%Y-%m-%d")

    # 오늘 통계
    today_drafts = [d for d in drafts if d.get("날짜") == today]
    today_publishes = [p for p in publishes if p.get("발행일시", "").startswith(today)]

    # 상태별 카운트
    status_counts = {}
    for d in drafts:
        s = d.get("상태", "알수없음")
        status_counts[s] = status_counts.get(s, 0) + 1

    # 블로그 타입별 카운트
    type_counts = {"dev": 0, "cpc": 0}
    for d in drafts:
        t = d.get("블로그타입", "")
        if t in type_counts:
            type_counts[t] += 1

    return {
        "today": today,
        "total_drafts": len(drafts),
        "total_published": len(publishes),
        "today_drafts": len(today_drafts),
        "today_published": len(today_publishes),
        "status_counts": status_counts,
        "type_counts": type_counts,
        "recent_drafts": today_drafts[-5:] if today_drafts else drafts[-5:],
        "recent_publishes": today_publishes[-5:] if today_publishes else publishes[-5:],
    }
