"""자동매매 대시보드 연동 모듈.

GCS 버킷에서 포지션/이력 조회 + KIS API로 현재가 조회.

.env 필요:
  KIS_APP_KEY=앱키
  KIS_APP_SECRET=시크릿키
  KIS_ACCOUNT_NO=계좌번호 (예: 64271098-01)
  KIS_POSITIONS_BUCKET=kis-trader-data-0626272957
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime

import httpx

KIS_BASE = "https://openapi.koreainvestment.com:9443"
GCS_PREFIX = "kis-trader/"


def _get_env(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        raise RuntimeError(f".env에 {key}를 설정해주세요.")
    return val


# ── GCS 데이터 읽기 (gsutil 사용 — gcloud 인증 활용) ──


GSUTIL = r"C:\Users\somem\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gsutil.cmd"


def _read_gcs_json(filename: str) -> dict | list:
    bucket_name = _get_env("KIS_POSITIONS_BUCKET")
    result = subprocess.run(
        [GSUTIL, "cat", f"gs://{bucket_name}/{GCS_PREFIX}{filename}"],
        capture_output=True, text=True, shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GCS 읽기 실패: {result.stderr}")
    return json.loads(result.stdout)


def _write_gcs_json(filename: str, data):
    bucket_name = _get_env("KIS_POSITIONS_BUCKET")
    json_str = json.dumps(data, ensure_ascii=False)
    result = subprocess.run(
        [GSUTIL, "cp", "-", f"gs://{bucket_name}/{GCS_PREFIX}{filename}"],
        input=json_str, capture_output=True, text=True, shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GCS 쓰기 실패: {result.stderr}")


def get_positions() -> dict:
    """현재 보유 포지션 조회."""
    return _read_gcs_json("position_meta.json")


def get_trade_history() -> list[dict]:
    """매매 이력 조회."""
    return _read_gcs_json("trade_history.json")


# ── KIS API ──


def _get_token() -> str:
    """KIS API 토큰 조회. 만료 시 재발급."""
    try:
        token_data = _read_gcs_json("token.json")
        expired_at = datetime.strptime(token_data["expired_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < expired_at:
            return token_data["access_token"]
    except Exception:
        pass

    # 토큰 재발급
    resp = httpx.post(
        f"{KIS_BASE}/oauth2/tokenP",
        json={
            "grant_type": "client_credentials",
            "appkey": _get_env("KIS_APP_KEY"),
            "appsecret": _get_env("KIS_APP_SECRET"),
        },
    )
    resp.raise_for_status()
    data = resp.json()

    token_data = {
        "access_token": data["access_token"],
        "expired_at": data.get("access_token_token_expired", ""),
    }
    _write_gcs_json("token.json", token_data)

    return data["access_token"]


def _kis_headers() -> dict:
    return {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {_get_token()}",
        "appkey": _get_env("KIS_APP_KEY"),
        "appsecret": _get_env("KIS_APP_SECRET"),
    }


def get_current_price(stock_code: str) -> dict:
    """종목 현재가 조회."""
    resp = httpx.get(
        f"{KIS_BASE}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers={
            **_kis_headers(),
            "tr_id": "FHKST01010100",
        },
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("rt_cd") != "0":
        return {"price": 0, "name": "조회실패", "change_pct": 0}

    output = data.get("output", {})
    return {
        "price": int(output.get("stck_prpr", 0)),
        "name": output.get("hts_kor_isnm", ""),
        "change_pct": float(output.get("prdy_ctrt", 0)),
        "high": int(output.get("stck_hgpr", 0)),
        "low": int(output.get("stck_lwpr", 0)),
        "volume": int(output.get("acml_vol", 0)),
    }


def get_account_balance() -> dict:
    """계좌 잔고 조회 (보유종목 + 총평가)."""
    account = _get_env("KIS_ACCOUNT_NO")
    acnt_no, acnt_prdt = account.split("-")

    resp = httpx.get(
        f"{KIS_BASE}/uapi/domestic-stock/v1/trading/inquire-balance",
        headers={
            **_kis_headers(),
            "tr_id": "TTTC8434R",
        },
        params={
            "CANO": acnt_no,
            "ACNT_PRDT_CD": acnt_prdt,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        },
    )
    resp.raise_for_status()
    data = resp.json()

    holdings = []
    for item in data.get("output1", []):
        qty = int(item.get("hldg_qty", 0))
        if qty == 0:
            continue
        buy_price = int(item.get("pchs_avg_pric", "0").split(".")[0])
        cur_price = int(item.get("prpr", 0))
        pnl = int(item.get("evlu_pfls_amt", 0))
        pnl_pct = float(item.get("evlu_pfls_rt", 0))

        holdings.append({
            "code": item.get("pdno", ""),
            "name": item.get("prdt_name", ""),
            "qty": qty,
            "buy_price": buy_price,
            "cur_price": cur_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    summary = data.get("output2", [{}])
    if isinstance(summary, list):
        summary = summary[0] if summary else {}

    return {
        "holdings": holdings,
        "total_eval": int(summary.get("tot_evlu_amt", 0)),
        "total_pnl": int(summary.get("evlu_pfls_smtl_amt", 0)),
        "total_buy": int(summary.get("pchs_amt_smtl_amt", 0)),
        "cash": int(summary.get("dnca_tot_amt", 0)),
    }


def get_trading_dashboard() -> dict:
    """대시보드용 트레이딩 데이터 통합 조회."""
    try:
        balance = get_account_balance()
    except Exception as e:
        balance = {"error": str(e), "holdings": [], "total_eval": 0, "total_pnl": 0, "cash": 0}

    try:
        history = get_trade_history()
    except Exception:
        history = []

    try:
        positions_meta = get_positions()
    except Exception:
        positions_meta = {}

    # 이력에서 오늘/이번주 수익 계산
    today = datetime.now().strftime("%Y-%m-%d")
    week_start = datetime.now()
    from datetime import timedelta
    day_of_week = week_start.weekday()
    week_start = (week_start - timedelta(days=day_of_week)).strftime("%Y-%m-%d")

    today_pnl = sum(t.get("pnl", 0) for t in history if t.get("date") == today)
    week_pnl = sum(t.get("pnl", 0) for t in history if t.get("date", "") >= week_start)
    total_realized = sum(t.get("pnl", 0) for t in history)

    # 보유종목에 메타데이터 병합
    for h in balance.get("holdings", []):
        meta = positions_meta.get(h["code"], {})
        h["atr_stop"] = meta.get("atr_stop", 0)
        h["atr_target"] = meta.get("atr_target", 0)
        h["buy_date"] = meta.get("buy_date", "")

    return {
        "balance": balance,
        "history": history,
        "positions_meta": positions_meta,
        "today_pnl": today_pnl,
        "week_pnl": week_pnl,
        "total_realized": total_realized,
        "unrealized_pnl": balance.get("total_pnl", 0),
    }
