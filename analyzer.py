from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from google import genai
from google.genai.types import GenerateContentConfig

from models import PatternReport, VideoAnalysis
from prompts import (
    ANALYZE_VIDEO_PROMPT,
    ANALYZE_VIDEO_STRUCTURED_PROMPT,
    EXTRACT_PATTERNS_PROMPT,
)

DOWNLOADS_DIR = Path(__file__).parent / "downloads"


def download_reel(url: str) -> Path:
    """yt-dlp로 릴스/숏폼 영상을 다운로드한다."""
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    output_template = str(DOWNLOADS_DIR / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "best[filesize<50M]/best",
        "-o", output_template,
        "--print", "after_move:filepath",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"다운로드 실패. yt-dlp 에러:\n{result.stderr}\n\n"
            "영상을 직접 다운로드해서 downloads/ 폴더에 넣고,\n"
            "  python main.py url --local downloads/파일명.mp4\n"
            "로 실행해주세요."
        )

    filepath = result.stdout.strip().splitlines()[-1]
    return Path(filepath)


def _upload_and_wait(video_path: Path, client: genai.Client):
    """Gemini에 영상을 업로드하고 처리 완료까지 대기한다."""
    print(f"영상 업로드 중... ({video_path.name})")
    video_file = client.files.upload(file=video_path)

    print("영상 처리 대기 중...")
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError("Gemini 영상 처리 실패")

    return video_file


def _clean_json(text: str) -> str:
    """Gemini 응답에서 JSON 부분만 추출한다."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def analyze_video(video_path: Path, client: genai.Client) -> str:
    """Gemini에 영상을 업로드하고 구조를 분석한다. (텍스트 반환 - 하위호환)"""
    video_file = _upload_and_wait(video_path, client)

    print("영상 분석 중...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[video_file, ANALYZE_VIDEO_PROMPT],
    )

    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    return response.text


def analyze_video_structured(
    video_path: Path, client: genai.Client, url: str = ""
) -> VideoAnalysis:
    """Gemini에 영상을 업로드하고 구조화된 분석 결과를 반환한다."""
    video_file = _upload_and_wait(video_path, client)

    print("영상 구조 분석 중...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[video_file, ANALYZE_VIDEO_STRUCTURED_PROMPT],
        config=GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    raw = _clean_json(response.text)
    data = json.loads(raw)
    data["url"] = url
    return VideoAnalysis.model_validate(data)


def analyze_batch(
    urls: list[str], client: genai.Client
) -> list[VideoAnalysis]:
    """여러 영상을 순차 다운로드 + 구조화 분석한다."""
    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")
        try:
            video_path = download_reel(url)
            analysis = analyze_video_structured(video_path, client, url=url)
            results.append(analysis)
            print(f"  ✓ 분석 완료: {analysis.title}")
        except Exception as e:
            print(f"  ✗ 실패: {e}")
    return results


def extract_patterns(
    analyses: list[VideoAnalysis], client: genai.Client
) -> PatternReport:
    """여러 분석 결과에서 공통 패턴을 추출한다."""
    analyses_json = json.dumps(
        [a.model_dump() for a in analyses],
        ensure_ascii=False,
        indent=2,
    )

    prompt = EXTRACT_PATTERNS_PROMPT.format(analyses_json=analyses_json)

    print("패턴 추출 중...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw = _clean_json(response.text)
    return PatternReport.model_validate_json(raw)


def format_analysis(analysis: VideoAnalysis) -> str:
    """VideoAnalysis를 읽기 좋은 텍스트로 포맷한다."""
    lines = [
        f"{'='*50}",
        f"📊 영상 분석: {analysis.title}",
        f"{'='*50}",
        f"URL: {analysis.url}" if analysis.url else "",
        f"총 길이: {analysis.total_duration_sec}초 | 씬 수: {len(analysis.scenes)}",
        "",
        f"🎣 훅 전략: {analysis.hook_strategy}",
        f"🏗️ 구조: {analysis.structure_pattern}",
        f"🎯 타겟: {analysis.target_audience}",
        f"🔥 바이럴 이유: {analysis.viral_reason}",
        "",
        f"🎵 BGM: {analysis.bgm_style}",
        f"⚡ 편집 속도: {analysis.editing_speed}",
        f"📝 자막 스타일: {analysis.text_style}",
        f"{'='*50}",
        "",
    ]

    for s in analysis.scenes:
        face = "👤 얼굴O" if s.face_visible else "🚫 얼굴X"
        lines.append(f"--- 씬 {s.scene_number} ({s.start_sec}s ~ {s.end_sec}s) [{s.mood}] {face} ---")
        lines.append(f"  화면: {s.visual}")
        if s.text_on_screen:
            lines.append(f"  자막: \"{s.text_on_screen}\"")
        if s.narration:
            lines.append(f"  나레이션: \"{s.narration}\"")
        lines.append(f"  전환: {s.transition}")
        lines.append("")

    return "\n".join(line for line in lines if line is not None)


def format_patterns(report: PatternReport) -> str:
    """PatternReport를 읽기 좋은 텍스트로 포맷한다."""
    lines = [
        f"{'='*50}",
        f"📈 패턴 분석 리포트 ({report.video_count}개 영상)",
        f"{'='*50}",
        "",
        f"⏱️ 평균 길이: {report.avg_duration_sec:.1f}초 | 평균 씬: {report.avg_scene_count:.1f}개",
        f"👤 얼굴 노출 비율: {report.face_visible_ratio:.0%}",
        "",
        "🎣 공통 훅 유형:",
    ]
    for h in report.common_hook_types:
        lines.append(f"  • {h}")

    lines.append(f"\n🏗️ 공통 구조: {report.common_structure}")

    lines.append("\n🎭 자주 쓰이는 분위기:")
    for m in report.common_moods:
        lines.append(f"  • {m}")

    lines.append("\n🔄 자주 쓰이는 전환:")
    for t in report.common_transitions:
        lines.append(f"  • {t}")

    lines.append("\n🔥 바이럴 요소:")
    for v in report.viral_factors:
        lines.append(f"  • {v}")

    lines.append(f"\n✂️ 편집 인사이트: {report.editing_insights}")

    lines.append(f"\n{'='*50}")
    lines.append("✅ 실행 가이드라인")
    lines.append(f"{'='*50}")
    for i, g in enumerate(report.actionable_guidelines, 1):
        lines.append(f"  {i}. {g}")

    return "\n".join(lines)
