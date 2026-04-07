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

CONTI_PROMPT_STORY = """너는 2026년 한국 숏폼 콘텐츠(릴스/숏츠) 전문 스크립트 작가야.

## TTS vs 자막 규칙 (매우 중요)
- tts_script: 소리로 들을 때 자연스러운 구어체. 길게 풀어서 말하듯이.
- subtitle_text: 화면에 짧게 보이는 텍스트. 핵심만. 임팩트.
둘은 반드시 다르게!

{reference_section}

## 내 썰: {story}
## 콘텐츠 유형: {content_type}

## 출력 규칙
1. 총 길이 15~60초. 첫 씬 훅, 마지막 CTA.
2. scene_type: text_overlay / ai_video
3. ai_video_prompt: 영어, "No background music, no voice, no text overlay, Cinematic, 24fps"

JSON: {{"title":"","total_duration_sec":0,"bgm_keywords":[],"font_recommendation":"","scenes":[{{"scene_number":1,"start_sec":0,"end_sec":3,"scene_type":"","visual_description":"","tts_script":"","subtitle_text":"","emphasis_keywords":[],"ai_video_prompt":null,"capcut_notes":""}}],"editing_summary":""}}
JSON만."""


CONTI_PROMPT_NEWS = """너는 2026년 한국 숏폼 콘텐츠(릴스/숏츠) 전문 스크립트 작가야.
국뽕+경제 정보 채널을 운영 중이야.

## 참고 영상 스타일 (반드시 따라할 것)
- 리스트형: "한국이 세계에서 유일하게 가능한 N가지" 포맷
- 총 길이 15~30초, 씬당 2~3초씩 빠르게 전환
- 구조: 훅(1초) → 도입(2초) → 리스트 아이템들(각 2초) → CTA(1초)
- 하드컷 전환, 빠른 속도감
- 모든 씬에 관련 AI 영상(ai_video) 사용

## TTS vs 자막 규칙
- tts_script: TTS로 읽을 대사. 빠르고 명확하게. 한 씬에 1~2문장.
  예: "첫 번째, 대한민국은 세계 유일의 반도체 메모리 자급 국가입니다."
- subtitle_text: 화면 텍스트. 핵심 키워드만. 숫자 + 짧은 문구.
  예: "1. 반도체 메모리 자급"
반드시 다르게 작성!

## 뉴스/토픽
{news_topics}

## 요청
위 뉴스/토픽을 바탕으로 국뽕+경제 숏폼 콘티를 만들어줘.
리스트형(N가지 이유/방법/사실)으로 만들고, 각 항목은 실제 사실에 기반해야 해.
허위 정보 절대 금지. 2026년 기준 정보만.

## 훅 예시 (이런 느낌으로)
- "한국에서만 가능한 것 5가지, 외국인들은 모릅니다"
- "전 세계가 한국을 부러워하는 진짜 이유"
- "한국 경제가 역대급인 6가지 근거"

## image_keywords 규칙 (매우 중요)
- 각 씬마다 image_keywords를 영어로 2~3개 작성
- 이 키워드로 스톡 이미지를 자동 검색함
- 씬 내용과 정확히 매칭되는 구체적 키워드 사용
- 예: ["semiconductor factory", "clean room"] (O)
- 예: ["korea"] (X — 너무 추상적)
- 예: ["Samsung Galaxy phone", "technology"] (O)

## scene_type
- 모든 씬은 "stock_image"로 설정 (스톡 이미지 자동 검색)
- ai_video_prompt는 사용하지 않음 (null)

## JSON 출력
{{"title":"","total_duration_sec":0,"bgm_keywords":["motivational","epic","korea"],"font_recommendation":"Pretendard Bold","scenes":[{{"scene_number":1,"start_sec":0,"end_sec":2,"scene_type":"stock_image","visual_description":"","tts_script":"","subtitle_text":"","emphasis_keywords":[],"image_keywords":["keyword1","keyword2"],"ai_video_prompt":null,"capcut_notes":"하드컷 전환"}}],"editing_summary":""}}
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


def generate_conti(story: str, content_type: str, client, analysis: str = "", news_topics: str = ""):
    if news_topics:
        # 국뽕+경제 뉴스 기반
        prompt = CONTI_PROMPT_NEWS.format(news_topics=news_topics)
    else:
        # 썰 기반
        reference = f"## 참고 영상 분석\n{analysis}\n위 영상의 구조를 모방하되 내용은 교체해." if analysis else ""
        prompt = CONTI_PROMPT_STORY.format(
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
    import traceback
    import shutil

    try:
        from tts import generate_all_scene_tts
        from scene_renderer import render_all_scenes
        from stock_media import fetch_all_scene_images
        from assembler import assemble_video
        from google.cloud import storage as gcs

        data = flask_request.json or {}
        conti_id = data.get("conti_id", "")
        conti_json = data.get("conti_json", "")
        voice = data.get("voice", "ko-KR-SunHiNeural")

        if not conti_json:
            ss = get_sheets()
            ws = ss.worksheet("릴스-콘티")
            records = ws.get_all_records()
            for r in records:
                if r.get("ID") == conti_id:
                    conti_json = str(r.get("콘티JSON", ""))
                    break

        if not conti_json:
            return {"error": "콘티를 찾을 수 없습니다"}, 404

        conti_data = json.loads(clean_json(conti_json))
        scenes = conti_data.get("scenes", [])
        print(f"[assemble] 시작: {conti_id}, {len(scenes)}개 씬")

        work_dir = Path(f"/tmp/assemble_{conti_id or 'temp'}")
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        tts_dir = work_dir / "tts"
        images_dir = work_dir / "images"
        output_path = work_dir / "output.mp4"

        # 1) TTS 생성
        print(f"[assemble] TTS 생성 중...")
        tts_paths = generate_all_scene_tts(scenes, tts_dir, voice)
        tts_count = sum(1 for p in tts_paths if p)
        print(f"[assemble] TTS {tts_count}개 완료")

        # 2) 스톡 이미지 자동 다운로드
        print(f"[assemble] 스톡 이미지 검색 중...", flush=True)
        stock_paths = fetch_all_scene_images(scenes, images_dir)
        stock_count = sum(1 for p in stock_paths if p)
        print(f"[assemble] 스톡 이미지 {stock_count}개 다운로드", flush=True)

        # 스톡 없는 씬은 텍스트 이미지로 대체
        for i, scene in enumerate(scenes):
            num = scene.get("scene_number", 0)
            img_path = images_dir / f"scene_{num:02d}.jpg"
            if not img_path.exists():
                render_all_scenes([scene], images_dir)
        image_paths = sorted(images_dir.glob("scene_*"))
        print(f"[assemble] 이미지 총 {len(image_paths)}개 완료", flush=True)

        # 3) FFmpeg 조립
        print(f"[assemble] FFmpeg 조립 중...")
        assemble_video(json.dumps(conti_data), images_dir, tts_dir, output_path)
        print(f"[assemble] 영상 조립 완료: {output_path}")

        # 4) 영상 파일을 /tmp에 유지하고 다운로드 ID 반환
        import uuid
        download_id = str(uuid.uuid4())[:8]
        final_path = Path(f"/tmp/video_{download_id}.mp4")
        shutil.copy2(output_path, final_path)
        shutil.rmtree(work_dir, ignore_errors=True)
        print(f"[assemble] 완료: {final_path}")

        return {
            "message": f"영상 조립 완료! TTS {tts_count}개, 씬 {len(scenes)}개",
            "download_id": download_id,
            "conti_id": conti_id,
        }, 200

    except Exception as e:
        print(f"[assemble] 에러: {traceback.format_exc()}")
        return {"error": f"조립 실패: {str(e)}"}, 500


@app.route("/scenes/<conti_id>", methods=["GET"])
def get_scenes_status(conti_id):
    """씬별 파일 상태 조회."""
    scene_dir = Path(f"/tmp/scenes_{conti_id}")
    scenes = []
    if scene_dir.exists():
        for f in sorted(scene_dir.iterdir()):
            scenes.append({"name": f.name, "size": f.stat().st_size, "type": f.suffix})
    return {"conti_id": conti_id, "files": scenes}, 200


@app.route("/scenes/<conti_id>/upload", methods=["POST"])
def upload_scene_file(conti_id):
    """씬별 파일 업로드 (이미지/영상)."""
    scene_num = flask_request.form.get("scene_number", "1")
    file = flask_request.files.get("file")
    if not file:
        return {"error": "파일이 없습니다"}, 400

    scene_dir = Path(f"/tmp/scenes_{conti_id}")
    scene_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix or ".mp4"
    save_path = scene_dir / f"scene_{int(scene_num):02d}{ext}"
    file.save(str(save_path))

    return {"message": f"씬 {scene_num} 업로드 완료", "path": str(save_path), "size": save_path.stat().st_size}, 200


@app.route("/scenes/<conti_id>/preview/<int:scene_num>", methods=["GET"])
def preview_scene_file(conti_id, scene_num):
    """업로드된 씬 파일 미리보기."""
    from flask import send_file
    scene_dir = Path(f"/tmp/scenes_{conti_id}")
    for ext in [".mp4", ".webm", ".mov", ".png", ".jpg", ".jpeg", ".gif"]:
        path = scene_dir / f"scene_{scene_num:02d}{ext}"
        if path.exists():
            mime = "video/mp4" if ext in [".mp4", ".webm", ".mov"] else f"image/{ext[1:]}"
            return send_file(str(path), mimetype=mime)
    return {"error": "파일 없음"}, 404


@app.route("/reassemble", methods=["POST"])
def reassemble():
    """업로드된 씬 파일로 재조립."""
    import traceback
    import shutil

    try:
        from tts import generate_all_scene_tts
        from scene_renderer import render_all_scenes
        from assembler import assemble_scene, concat_scenes
        from mutagen.mp3 import MP3

        data = flask_request.json or {}
        conti_id = data.get("conti_id", "")
        conti_json = data.get("conti_json", "")
        voice = data.get("voice", "ko-KR-SunHiNeural")

        if not conti_json:
            ss = get_sheets()
            ws = ss.worksheet("릴스-콘티")
            for r in ws.get_all_records():
                if r.get("ID") == conti_id:
                    conti_json = str(r.get("콘티JSON", ""))
                    break

        if not conti_json:
            return {"error": "콘티를 찾을 수 없습니다"}, 404

        conti_data = json.loads(clean_json(conti_json))
        scenes = conti_data.get("scenes", [])

        scene_dir = Path(f"/tmp/scenes_{conti_id}")
        work_dir = Path(f"/tmp/reassemble_{conti_id}")
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        tts_dir = work_dir / "tts"
        default_images_dir = work_dir / "default_images"

        # TTS 생성
        tts_paths = generate_all_scene_tts(scenes, tts_dir, voice)

        # 기본 이미지 생성 (업로드 안 된 씬용)
        render_all_scenes(scenes, default_images_dir)

        # 씬별 영상 클립 생성
        scene_videos = []
        for scene in scenes:
            num = scene.get("scene_number", 0)
            start = scene.get("start_sec", 0)
            end = scene.get("end_sec", 3)
            duration = end - start

            # 업로드된 파일 확인
            uploaded = None
            if scene_dir.exists():
                for ext in [".mp4", ".webm", ".mov", ".png", ".jpg", ".jpeg", ".gif"]:
                    candidate = scene_dir / f"scene_{num:02d}{ext}"
                    if candidate.exists():
                        uploaded = candidate
                        break

            # TTS
            tts_path = tts_dir / f"scene_{num:02d}.mp3"
            if not tts_path.exists():
                tts_path = None

            scene_output = work_dir / f"clip_{num:02d}.mp4"

            if uploaded and uploaded.suffix in [".mp4", ".webm", ".mov"]:
                # 업로드된 영상 + TTS 합성
                import subprocess
                if tts_path:
                    cmd = ["ffmpeg", "-y", "-i", str(uploaded), "-i", str(tts_path),
                           "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                           "-pix_fmt", "yuv420p", "-shortest", str(scene_output)]
                else:
                    cmd = ["ffmpeg", "-y", "-i", str(uploaded),
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", str(scene_output)]
                subprocess.run(cmd, capture_output=True)
            elif uploaded and uploaded.suffix in [".png", ".jpg", ".jpeg", ".gif"]:
                # 업로드된 이미지 + TTS
                assemble_scene(uploaded, tts_path, duration, scene_output)
            else:
                # 기본 생성 이미지 사용
                default_img = None
                for ext in [".png"]:
                    for prefix in [f"scene_{num:02d}", f"scene_{num:02d}_placeholder"]:
                        candidate = default_images_dir / f"{prefix}{ext}"
                        if candidate.exists():
                            default_img = candidate
                            break
                if default_img:
                    assemble_scene(default_img, tts_path, duration, scene_output)

            if scene_output.exists():
                scene_videos.append(scene_output)

        if not scene_videos:
            return {"error": "조립할 씬이 없습니다"}, 400

        # 이어붙이기
        import uuid
        download_id = str(uuid.uuid4())[:8]
        final_path = Path(f"/tmp/video_{download_id}.mp4")
        concat_scenes(scene_videos, final_path)

        # 작업 파일 정리
        shutil.rmtree(work_dir, ignore_errors=True)

        return {
            "message": f"재조립 완료! {len(scene_videos)}개 씬",
            "download_id": download_id,
            "conti_id": conti_id,
        }, 200

    except Exception as e:
        import traceback
        print(f"[reassemble] 에러: {traceback.format_exc()}", flush=True)
        return {"error": f"재조립 실패: {str(e)}"}, 500


@app.route("/download/<download_id>", methods=["GET"])
def download_video_file(download_id):
    """조립된 영상 다운로드."""
    from flask import send_file
    path = Path(f"/tmp/video_{download_id}.mp4")
    if not path.exists():
        return {"error": "파일을 찾을 수 없습니다. 다시 조립해주세요."}, 404
    return send_file(str(path), mimetype="video/mp4", as_attachment=True, download_name=f"reel_{download_id}.mp4")


@app.route("/daily-shorts", methods=["POST", "GET"])
def daily_shorts():
    """매일 국뽕+경제 숏폼 콘티 자동 생성."""
    from news import get_trending_topics

    ss = get_sheets()
    gemini = get_gemini()
    ws_conti = ss.worksheet("릴스-콘티")

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    try:
        # 1) 트렌딩 뉴스 수집
        topics = get_trending_topics()
        if not topics:
            return {"message": "트렌딩 토픽을 가져올 수 없습니다"}, 200

        topics_text = "\n".join([
            f"- {t['title']} (출처: {t.get('source', 'unknown')})"
            for t in topics[:10]
        ])

        # 2) Gemini로 콘티 생성
        conti_raw = generate_conti("", "", gemini, news_topics=topics_text)
        conti_json = clean_json(conti_raw)

        try:
            conti_data = json.loads(conti_json)
            title = conti_data.get("title", "국뽕+경제 숏폼")
            duration = conti_data.get("total_duration_sec", 0)
        except Exception:
            title = "국뽕+경제 숏폼"
            duration = 0

        # 3) 시트에 저장
        ids = ws_conti.col_values(1)[1:]
        prefix = "R" + today.replace("-", "")
        seq = len([i for i in ids if i.startswith(prefix)]) + 1
        conti_id = f"{prefix}-{seq:03d}"

        ws_conti.append_row([
            conti_id, today, time_str, title, "국뽕+경제",
            duration, "초안", "", conti_json, "",
        ], value_input_option="RAW")

        return {
            "message": f"숏폼 콘티 생성 완료! ({conti_id})",
            "conti_id": conti_id,
            "title": title,
            "topics_used": len(topics),
        }, 200

    except Exception as e:
        import traceback
        print(f"[daily-shorts] 에러: {traceback.format_exc()}", flush=True)
        return {"error": str(e)}, 500


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
                blog_prompt = f"""10년차 시니어 개발자이자 SEO 전문가. 티스토리 개발 블로그 "개발막차" 글 작성.
규칙: 2026년 기준. 실제 정보만. "(확인 필요)" 같은 메타 표시 금지.
SEO: 제목에 키워드 앞쪽 배치 + "2026". H2 모두 키워드 변형 포함 (인사말 H2 금지). 첫 문장 키워드로 시작 (인사말 없이 바로 본론). 서론 3줄 이내.
키워드: {keyword}. 톤: ~거든요/~인데요 체. 코드블록 필수. 2000~3000자.
JSON: {{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[],"estimated_reading_min":5,"cpc_category":""}}
JSON만."""
            else:
                blog_prompt = f"""청년 경제/재테크 전문 블로거. 티스토리 CPC 블로그 글 작성.
규칙: 2026년 기준. 실제 정보만. 없는 제도 금지. "(확인 필요)" 본문에 넣지 말고 "정확한 조건은 [기관명] 홈페이지에서 확인하세요"로 안내.
SEO: 제목에 키워드 앞쪽 + "2026" + 숫자. H2 모두 키워드 변형 (감성 H2 금지). 첫 문장 키워드+핵심 수치로 시작. 서론 3줄 이내. 비교표 1개 필수.
키워드: {keyword}. 톤: ~입니다 기본 + ~거든요 섞기. 2500~3500자. 면책조항 마지막에.
JSON: {{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[],"estimated_reading_min":7,"cpc_category":"청년 지원금"}}
JSON만."""

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

    # 매매 이력 — GCS에서 읽어서 시트에 없는 것만 추가
    new_history = 0
    try:
        import subprocess as _sp
        gcs_result = _sp.run(
            ["gsutil", "cat", f"gs://{os.getenv('KIS_POSITIONS_BUCKET', '')}/kis-trader/trade_history.json"],
            capture_output=True, text=True,
        )
        if gcs_result.returncode == 0:
            trade_history = json.loads(gcs_result.stdout)
        else:
            trade_history = []
    except Exception:
        trade_history = []

    if trade_history:
        ws_hist = ss.worksheet("매매-이력")
        existing_hist = ws_hist.get_all_values()[1:]
        existing_set = {(r[0], r[1]) for r in existing_hist}
        for t in trade_history:
            key = (t.get("date", ""), t.get("code", ""))
            if key not in existing_set:
                ws_hist.append_row([
                    t.get("date", ""), t.get("code", ""), t.get("name", ""),
                    t.get("pnl_pct", 0), t.get("pnl", 0),
                ], value_input_option="RAW")
                new_history += 1

    return {"message": f"동기화 완료: 평가 {total_eval:,}원, 종목 {len(holdings)}개, 이력 +{new_history}건"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
