"""장 마감 후 KIS 잔고/이력 → 구글 시트 동기화.

사용법:
  python sync_trading.py

GitHub Actions에서 매일 15:40 KST에 실행.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── GCS 읽기 ──

GSUTIL = os.getenv("GSUTIL_PATH", "gsutil")
BUCKET = os.getenv("KIS_POSITIONS_BUCKET", "")
GCS_PREFIX = "kis-trader/"


def read_gcs_json(filename: str):
    result = subprocess.run(
        [GSUTIL, "cat", f"gs://{BUCKET}/{GCS_PREFIX}{filename}"],
        capture_output=True, text=True, shell=(os.name == "nt"),
    )
    if result.returncode != 0:
        raise RuntimeError(f"GCS 읽기 실패: {result.stderr}")
    return json.loads(result.stdout)


# ── KIS API ──

import httpx

KIS_BASE = "https://openapi.koreainvestment.com:9443"


def get_token() -> str:
    try:
        token_data = read_gcs_json("token.json")
        expired = datetime.strptime(token_data["expired_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < expired:
            return token_data["access_token"]
    except Exception:
        pass

    resp = httpx.post(f"{KIS_BASE}/oauth2/tokenP", json={
        "grant_type": "client_credentials",
        "appkey": os.getenv("KIS_APP_KEY", ""),
        "appsecret": os.getenv("KIS_APP_SECRET", ""),
    })
    data = resp.json()
    return data["access_token"]


def kis_headers(token: str) -> dict:
    return {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("KIS_APP_KEY", ""),
        "appsecret": os.getenv("KIS_APP_SECRET", ""),
    }


def get_balance(token: str) -> dict:
    acnt = os.getenv("KIS_ACCOUNT_NO", "").split("-")
    params = {
        "CANO": acnt[0], "ACNT_PRDT_CD": acnt[1],
        "AFHR_FLPR_YN": "N", "OFL_YN": "",
        "INQR_DVSN": "02", "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01", "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
    }
    resp = httpx.get(
        f"{KIS_BASE}/uapi/domestic-stock/v1/trading/inquire-balance",
        headers={**kis_headers(token), "tr_id": "TTTC8434R"},
        params=params,
    )
    return resp.json()


# ── 구글 시트 저장 ──

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets():
    cred_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
    creds = Credentials.from_service_account_file(cred_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(os.getenv("GOOGLE_SHEETS_ID", ""))


def sync():
    print("KIS 잔고 조회 중...")
    token = get_token()
    balance_data = get_balance(token)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # 보유종목 파싱
    holdings = []
    for item in balance_data.get("output1", []):
        qty = int(item.get("hldg_qty", 0))
        if qty == 0:
            continue
        holdings.append({
            "code": item.get("pdno", ""),
            "name": item.get("prdt_name", ""),
            "qty": qty,
            "buy_price": int(item.get("pchs_avg_pric", "0").split(".")[0]),
            "cur_price": int(item.get("prpr", 0)),
            "pnl_pct": float(item.get("evlu_pfls_rt", 0)),
            "pnl": int(item.get("evlu_pfls_amt", 0)),
        })

    summary = balance_data.get("output2", [{}])
    if isinstance(summary, list):
        summary = summary[0] if summary else {}

    total_eval = int(summary.get("tot_evlu_amt", 0))
    total_buy = int(summary.get("pchs_amt_smtl_amt", 0))
    total_pnl = int(summary.get("evlu_pfls_smtl_amt", 0))
    cash = int(summary.get("dnca_tot_amt", 0))

    # GCS에서 포지션 메타 + 매매 이력 읽기
    try:
        positions_meta = read_gcs_json("position_meta.json")
    except Exception:
        positions_meta = {}

    try:
        trade_history = read_gcs_json("trade_history.json")
    except Exception:
        trade_history = []

    # 구글 시트 저장
    print("구글 시트 저장 중...")
    ss = get_sheets()

    # 1) 잔고 시트 — 오늘 행 추가 (중복 방지)
    ws_balance = ss.worksheet("매매-잔고")
    existing_dates = ws_balance.col_values(1)[1:]
    if today not in existing_dates:
        ws_balance.append_row([
            today, time_str, total_eval, total_buy, total_pnl,
            cash, len(holdings),
        ], value_input_option="RAW")
        print(f"  잔고 저장: 평가 {total_eval:,}원, 손익 {total_pnl:,}원")
    else:
        # 오늘 이미 있으면 업데이트
        row_idx = existing_dates.index(today) + 2  # 1-indexed + header
        ws_balance.update(f"A{row_idx}:G{row_idx}", [[
            today, time_str, total_eval, total_buy, total_pnl,
            cash, len(holdings),
        ]])
        print(f"  잔고 업데이트: 평가 {total_eval:,}원, 손익 {total_pnl:,}원")

    # 2) 보유종목 시트 — 오늘 데이터 교체
    ws_holdings = ss.worksheet("매매-보유종목")
    all_holdings = ws_holdings.get_all_values()
    # 오늘 날짜 행 삭제 (뒤에서부터)
    rows_to_delete = [i + 1 for i, row in enumerate(all_holdings) if i > 0 and row[0] == today]
    for row_idx in reversed(rows_to_delete):
        ws_holdings.delete_rows(row_idx)

    # 새로 추가
    for h in holdings:
        meta = positions_meta.get(h["code"], {})
        ws_holdings.append_row([
            today, h["code"], h["name"], h["qty"],
            h["buy_price"], h["cur_price"],
            h["pnl_pct"], h["pnl"],
            meta.get("atr_stop", ""), meta.get("atr_target", ""),
            meta.get("buy_date", ""),
        ], value_input_option="RAW")
    print(f"  보유종목 {len(holdings)}개 저장")

    # 3) 매매이력 시트 — GCS 이력에서 시트에 없는 것만 추가
    ws_history = ss.worksheet("매매-이력")
    existing_history = ws_history.get_all_values()[1:]  # 헤더 제외
    existing_set = {(r[0], r[1]) for r in existing_history}  # (날짜, 종목코드)

    new_count = 0
    for t in trade_history:
        key = (t.get("date", ""), t.get("code", ""))
        if key not in existing_set:
            ws_history.append_row([
                t.get("date", ""), t.get("code", ""), t.get("name", ""),
                t.get("pnl_pct", 0), t.get("pnl", 0),
            ], value_input_option="RAW")
            new_count += 1
    print(f"  매매이력 {new_count}개 추가")

    print("\n동기화 완료!")


if __name__ == "__main__":
    sync()
