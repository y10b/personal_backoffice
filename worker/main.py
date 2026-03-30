"""릴스 콘티 워커 — Cloud Run에서 실행.

시트에서 "대기" 요청을 가져와서 처리하고 결과를 시트에 저장.
Pub/Sub 트리거 또는 Cloud Scheduler로 1분마다 호출.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import gspread
from dotenv import load_dotenv
from flask import Flask, request as flask_request
from google import genai
from google.genai.types import GenerateContentConfig
from google.oauth2.service_account import Credentials

load_dotenv()

app = Flask(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DOWNLOADS_DIR = Path("/tmp/downloads")


def get_sheets():
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    if creds_json:
        import json as _json
        info = _json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        cred_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
        creds = Credentials.from_service_account_file(cred_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(os.getenv("GOOGLE_SHEETS_ID", ""))


def get_gemini():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))


ANALYZE_PROMPT = """이 릴스/숏폼 영상을 분석해서 JSON으로 출력해줘.

다음 JSON 스키마에 맞춰서 출력해:
{
  "title": "영상 제목/설명",
  "total_duration_sec": 총길이(초),
  "scenes": [{"scene_number":1,"start_sec":0,"end_sec":3,"visual":"","text_on_screen":"","narration":"","mood":"","transition":"","face_visible":true}],
  "hook_strategy": "", "structure_pattern": "", "target_audience": "", "viral_reason": "",
  "bgm_style": "", "editing_speed": "", "text_style": ""
}
한국어로, JSON만 출력해."""

CONTI_PROMPT = """너는 2026년 한국 숏폼 콘텐츠(릴스/숏츠) 전문 스크립트 작가이자 콘티 작성자야.

## 크리에이터 정보
- 상황: 알바생 + 개발자 + 창업 준비 중
- 스타일: 얼굴 노출 없음, CapCut 편집, CapCut TTS
- 이름 노출 절대 안 함

## TTS vs 자막 규칙 (매우 중요)
tts_script와 subtitle_text는 반드시 다르게 작성해!
- tts_script: 소리로 들을 때 자연스러운 구어체. 길게 풀어서 말하듯이.
  예: "아니 근데 진짜 미쳤는 게 이거 첫날인데 감자튀김을 통째로 바닥에 쏟았거든요"
- subtitle_text: 화면에 짧게 보이는 텍스트. 핵심만. 임팩트 있게.
  예: "첫날 감자튀김 통째로 쏟음"

TTS는 귀로 듣는 거고, 자막은 눈으로 스캔하는 거야. 같으면 안 돼!

## 2026년 MZ 숏폼 말투 가이드
- 말하듯이 자연스럽게. 글로 읽히면 안 됨
- 과장 리액션 자연스럽게: "아 ㅋㅋ 이거 실화냐고", "진짜 소름이었거든"
- 쉬는 타이밍 표시: "..." 또는 "근데요," 로 호흡 넣기
- 현재 유행 표현: "역대급", "ㄹㅇ", "찐", "쌰갈", "갓생"
- 주의: 유행어 남발 X. 훅/반전/마무리에만 임팩트있게

{reference_section}

## 내 썰/콘텐츠
{story}

## 콘텐츠 유형
{content_type}

## 출력 규칙
1. 총 길이 15~60초
2. 첫 씬은 훅 (1~3초) — "퇴사한 알바생이 사실 AI 개발자?" 이런 식 아님! 구체적 상황으로 시작
   좋은 훅: "감자튀김 200인분을 바닥에 쏟아버렸습니다..." (구체적 상황)
   나쁜 훅: "퇴사한 알바생이 사실 개발자?" (뻔함, 유튜브 제목 느낌)
3. 마지막 씬은 CTA
4. scene_type: text_overlay / ai_video / screen_recording
5. ai_video_prompt: 영어, "No background music, no voice, no text overlay, Cinematic, 24fps"
6. tts_script: 반드시 말하는 느낌으로. subtitle_text와 다르게!
7. subtitle_text: 짧고 임팩트. emphasis_keywords로 강조할 단어 지정

JSON 출력:
{{"title":"","total_duration_sec":0,"bgm_keywords":[],"font_recommendation":"","scenes":[{{"scene_number":1,"start_sec":0,"end_sec":3,"scene_type":"","visual_description":"","tts_script":"","subtitle_text":"","emphasis_keywords":[],"ai_video_prompt":null,"capcut_notes":""}}],"editing_summary":""}}
JSON만 출력해."""


def download_video(url: str) -> Path:
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    output_template = str(DOWNLOADS_DIR / "%(id)s.%(ext)s")
    result = subprocess.run(
        ["yt-dlp", "--no-playlist", "-f", "best[filesize<50M]/best",
         "-o", output_template, "--print", "after_move:filepath", url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"다운로드 실패: {result.stderr}")
    return Path(result.stdout.strip().splitlines()[-1])


def analyze_video(video_path: Path, client):
    video_file = client.files.upload(file=video_path)
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = client.files.get(name=video_file.name)
    if video_file.state.name == "FAILED":
        raise RuntimeError("영상 처리 실패")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[video_file, ANALYZE_PROMPT],
        config=GenerateContentConfig(response_mime_type="application/json"),
    )
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass
    return response.text


def generate_conti(story: str, content_type: str, client, analysis: str = ""):
    if analysis:
        reference = f"## 참고 영상 분석\n{analysis}\n위 영상의 구조를 모방하되 내용은 교체해."
    else:
        reference = ""

    prompt = CONTI_PROMPT.format(
        reference_section=reference,
        story=story,
        content_type=content_type,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=GenerateContentConfig(response_mime_type="application/json"),
    )
    return response.text


def clean_json(text: str) -> str:
    import re
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def process_request(row_idx: int, req_data: dict, ss, gemini):
    ws_req = ss.worksheet("릴스-요청")
    ws_conti = ss.worksheet("릴스-콘티")

    # 상태를 "처리중"으로
    ws_req.update_cell(row_idx, 8, "처리중")

    try:
        req_type = req_data.get("타입", "story")
        url = req_data.get("URL", "")
        story = req_data.get("썰", "")
        content_type = req_data.get("콘텐츠유형", "알바 썰")

        analysis = ""
        if req_type == "url" and url:
            video_path = download_video(url)
            analysis = analyze_video(video_path, gemini)

        if not story and analysis:
            # 분석만
            conti_json = analysis
            title = "영상 분석"
        else:
            conti_raw = generate_conti(story, content_type, gemini, analysis)
            conti_json = clean_json(conti_raw)
            try:
                title = json.loads(conti_json).get("title", "콘티")
            except Exception:
                title = "콘티"

        # 콘티 시트에 저장
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        ids = ws_conti.col_values(1)[1:]
        prefix = "R" + today.replace("-", "")
        seq = len([i for i in ids if i.startswith(prefix)]) + 1
        conti_id = f"{prefix}-{seq:03d}"

        try:
            duration = json.loads(conti_json).get("total_duration_sec", 0)
        except Exception:
            duration = 0

        ws_conti.append_row([
            conti_id, today, time_str, title, content_type,
            duration, "초안", url, conti_json, "",
        ], value_input_option="RAW")

        # 요청 상태를 "완료"로
        ws_req.update_cell(row_idx, 8, "완료")
        return conti_id

    except Exception as e:
        ws_req.update_cell(row_idx, 8, f"실패: {str(e)[:100]}")
        raise


@app.route("/", methods=["POST", "GET"])
def handle():
    """대기 중인 요청을 처리."""
    ss = get_sheets()
    gemini = get_gemini()

    ws = ss.worksheet("릴스-요청")
    rows = ws.get_all_records()

    pending = [(i + 2, r) for i, r in enumerate(rows) if r.get("상태") == "대기"]

    if not pending:
        return {"message": "처리할 요청 없음"}, 200

    results = []
    for row_idx, req_data in pending:
        try:
            conti_id = process_request(row_idx, req_data, ss, gemini)
            results.append({"id": req_data.get("ID"), "conti_id": conti_id, "status": "완료"})
        except Exception as e:
            results.append({"id": req_data.get("ID"), "status": "실패", "error": str(e)})

    return {"processed": len(results), "results": results}, 200


@app.route("/assemble", methods=["POST"])
def assemble():
    """콘티 → TTS + 이미지 → 영상 조립."""
    from tts import generate_all_scene_tts
    from scene_renderer import render_all_scenes
    from assembler import assemble_video
    from google.cloud import storage as gcs

    data = flask_request.json or {}
    conti_id = data.get("conti_id", "")
    conti_json = data.get("conti_json", "")
    voice = data.get("voice", "ko-KR-SunHiNeural")

    if not conti_json:
        # 시트에서 가져오기
        ss = get_sheets()
        ws = ss.worksheet("릴스-콘티")
        records = ws.get_all_records()
        for r in records:
            if r.get("ID") == conti_id:
                conti_json = r.get("콘티JSON", "")
                break

    if not conti_json:
        return {"error": "콘티를 찾을 수 없습니다"}, 404

    try:
        conti_data = json.loads(clean_json(conti_json))
        scenes = conti_data.get("scenes", [])

        work_dir = Path(f"/tmp/assemble_{conti_id or 'temp'}")
        work_dir.mkdir(parents=True, exist_ok=True)
        tts_dir = work_dir / "tts"
        images_dir = work_dir / "images"
        output_path = work_dir / "output.mp4"

        # 1) TTS 생성
        print(f"TTS 생성 중... ({len(scenes)}개 씬)")
        tts_paths = generate_all_scene_tts(scenes, tts_dir, voice)
        tts_count = sum(1 for p in tts_paths if p)

        # 2) 씬 이미지 생성
        print(f"씬 이미지 생성 중...")
        image_paths = render_all_scenes(scenes, images_dir)

        # 3) FFmpeg 조립
        print(f"영상 조립 중...")
        assemble_video(json.dumps(conti_data), images_dir, tts_dir, output_path)

        # 4) GCS에 업로드 (다운로드 링크용)
        bucket_name = os.getenv("KIS_POSITIONS_BUCKET", "")
        if bucket_name:
            gcs_client = gcs.Client()
            bucket = gcs_client.bucket(bucket_name)
            blob_name = f"videos/{conti_id or 'temp'}.mp4"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(output_path), content_type="video/mp4")
            blob.make_public()
            video_url = blob.public_url
        else:
            video_url = ""

        # 정리
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)

        return {
            "message": f"영상 조립 완료! TTS {tts_count}개, 씬 {len(scenes)}개",
            "video_url": video_url,
            "conti_id": conti_id,
        }, 200

    except Exception as e:
        return {"error": f"조립 실패: {str(e)}"}, 500


@app.route("/daily-drafts", methods=["POST", "GET"])
def daily_drafts():
    """매일 블로그 초안 2개 생성 (dev + cpc)."""
    ss = get_sheets()
    gemini = get_gemini()
    ws_draft = ss.worksheet("블로그-초안")

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    results = []

    for blog_type, type_desc, extra in [
        ("dev", "개발 블로그", "개발자/IT 종사자가 검색하는 키워드"),
        ("cpc", "청년 N잡러 경제 정보 블로그", "광고 단가(CPC)가 높은 청년 지원금/프리랜서 세금/N잡 경제 키워드"),
    ]:
        try:
            # 키워드 추천
            kw_prompt = f"SEO 키워드 리서치 전문가야. {type_desc}용 키워드 1개 추천. 검색량 있고 경쟁 낮은 롱테일. JSON: {{\"keyword\":\"키워드\"}} 만 출력."
            kw_res = gemini.models.generate_content(
                model="gemini-2.5-flash", contents=kw_prompt,
                config=GenerateContentConfig(response_mime_type="application/json"),
            )
            keyword = json.loads(clean_json(kw_res.text)).get("keyword", "개발 팁" if blog_type == "dev" else "청년 지원금")

            # 글 생성
            if blog_type == "dev":
                blog_prompt = f"""개발 블로그 전문 작가. SEO 최적화 글 작성.
중요: 현재 2026년. 실제 존재하는 정확한 정보만 사용. 추측/지어내기 금지. 버전/명령어/API는 실제 것만.
키워드: {keyword}. 톤: 친근한 ~해요체. 독자: 주니어 개발자.
H2 3~5개, 1500~2500자, 제목에 2026 포함 권장, 마지막에 CTA.
JSON: {{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[],"estimated_reading_min":5,"cpc_category":""}}
JSON만 출력."""
            else:
                blog_prompt = f"""청년 N잡러 경제 블로그 작가. SEO 최적화 정보성 글.
중요: 현재 2026년. 실제 존재하는 정확한 정보만 사용. 지원금/금리/조건은 2026년 실제 데이터 기준. 없는 제도 지어내지 마. 불확실하면 "확인 필요" 표시. 면책조항: "2026년 기준 정보이며, 정확한 내용은 관련 기관에 확인하세요."
키워드: {keyword}. 독자: 20~30대 청년, 프리랜서.
H2 4~6개, 2000~3000자, 비교표/리스트 활용, 제목에 2026 포함 권장.
JSON: {{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[],"estimated_reading_min":7,"cpc_category":"청년 지원금"}}
JSON만 출력."""

            post_res = gemini.models.generate_content(
                model="gemini-2.5-flash", contents=blog_prompt,
                config=GenerateContentConfig(response_mime_type="application/json"),
            )
            post = json.loads(clean_json(post_res.text))

            # 시트에 저장
            ids = ws_draft.col_values(1)[1:]
            prefix = today.replace("-", "")
            seq = len([i for i in ids if i.startswith(prefix)]) + 1
            draft_id = f"{prefix}-{seq:03d}"

            ws_draft.append_row([
                draft_id, today, time_str, blog_type, post.get("cpc_category", ""),
                post.get("title", ""), ", ".join(post.get("keywords", [])),
                post.get("slug", ""), post.get("category", ""),
                ", ".join(post.get("tags", [])), post.get("meta_description", ""),
                str(post.get("estimated_reading_min", 5)), "초안",
                post.get("html_content", ""), json.dumps(post.get("images", []), ensure_ascii=False), "",
            ], value_input_option="RAW")

            results.append({"blog_type": blog_type, "draft_id": draft_id, "title": post.get("title", "")})
        except Exception as e:
            results.append({"blog_type": blog_type, "error": str(e)})

    return {"message": f"블로그 초안 {len(results)}개 처리", "results": results}, 200


@app.route("/sync-trading", methods=["POST", "GET"])
def sync_trading():
    """장 마감 후 KIS 잔고 → 구글 시트 동기화."""
    import httpx

    ss = get_sheets()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    KIS_BASE = "https://openapi.koreainvestment.com:9443"
    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    account = os.getenv("KIS_ACCOUNT_NO", "").split("-")

    # 토큰 발급
    token_res = httpx.post(f"{KIS_BASE}/oauth2/tokenP", json={
        "grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret,
    })
    token = token_res.json().get("access_token", "")

    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": app_key, "appsecret": app_secret, "tr_id": "TTTC8434R",
    }

    # 잔고 조회
    bal_res = httpx.get(f"{KIS_BASE}/uapi/domestic-stock/v1/trading/inquire-balance", headers=headers, params={
        "CANO": account[0], "ACNT_PRDT_CD": account[1],
        "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
    })
    bal_data = bal_res.json()

    holdings = []
    for item in bal_data.get("output1", []):
        qty = int(item.get("hldg_qty", 0))
        if qty == 0:
            continue
        holdings.append({
            "code": item.get("pdno", ""), "name": item.get("prdt_name", ""),
            "qty": qty, "buy_price": int(item.get("pchs_avg_pric", "0").split(".")[0]),
            "cur_price": int(item.get("prpr", 0)),
            "pnl_pct": float(item.get("evlu_pfls_rt", 0)),
            "pnl": int(item.get("evlu_pfls_amt", 0)),
        })

    summary = bal_data.get("output2", [{}])
    if isinstance(summary, list):
        summary = summary[0] if summary else {}

    total_eval = int(summary.get("tot_evlu_amt", 0))
    total_buy = int(summary.get("pchs_amt_smtl_amt", 0))
    total_pnl = int(summary.get("evlu_pfls_smtl_amt", 0))
    cash = int(summary.get("dnca_tot_amt", 0))

    # 잔고 시트
    ws_bal = ss.worksheet("매매-잔고")
    existing = ws_bal.col_values(1)[1:]
    if today in existing:
        row_idx = existing.index(today) + 2
        ws_bal.update(f"A{row_idx}:G{row_idx}", [[today, time_str, total_eval, total_buy, total_pnl, cash, len(holdings)]])
    else:
        ws_bal.append_row([today, time_str, total_eval, total_buy, total_pnl, cash, len(holdings)], value_input_option="RAW")

    # 보유종목 시트
    ws_hold = ss.worksheet("매매-보유종목")
    all_rows = ws_hold.get_all_values()
    rows_to_del = [i + 1 for i, r in enumerate(all_rows) if i > 0 and r[0] == today]
    for idx in reversed(rows_to_del):
        ws_hold.delete_rows(idx)

    for h in holdings:
        ws_hold.append_row([today, h["code"], h["name"], h["qty"], h["buy_price"], h["cur_price"], h["pnl_pct"], h["pnl"], "", "", ""], value_input_option="RAW")

    return {"message": f"동기화 완료: 평가 {total_eval:,}원, 종목 {len(holdings)}개"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
