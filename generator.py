from __future__ import annotations

import json
import re

from google import genai
from google.genai.types import GenerateContentConfig

from models import Conti
from prompts import GENERATE_CONTI_PROMPT, GENERATE_FROM_REFERENCE_PROMPT


def _clean_json(text: str) -> str:
    """Gemini 응답에서 JSON 부분만 추출한다."""
    # 마크다운 코드블록 제거
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _call_gemini(prompt: str, client: genai.Client) -> Conti:
    """Gemini를 호출하고 JSON 응답을 Conti로 파싱한다."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw = _clean_json(response.text)

    try:
        return Conti.model_validate_json(raw)
    except Exception:
        # JSON 파싱 실패 시 한 번 더 시도
        data = json.loads(raw)
        return Conti.model_validate(data)


def generate_from_story(
    story: str, content_type: str, client: genai.Client
) -> Conti:
    """썰/텍스트에서 바로 콘티를 생성한다."""
    prompt = GENERATE_CONTI_PROMPT.format(
        input_content=story,
        content_type=content_type,
    )
    return _call_gemini(prompt, client)


def generate_from_reference(
    video_analysis: str,
    story: str,
    content_type: str,
    client: genai.Client,
) -> Conti:
    """참고 영상 분석 + 내 썰을 결합해 콘티를 생성한다."""
    prompt = GENERATE_FROM_REFERENCE_PROMPT.format(
        video_analysis=video_analysis,
        story_text=story,
        content_type=content_type,
    )
    return _call_gemini(prompt, client)


def format_conti(conti: Conti) -> str:
    """Conti 객체를 읽기 좋은 텍스트로 포맷한다."""
    lines = [
        f"{'='*50}",
        f"🎬 콘티: {conti.title}",
        f"{'='*50}",
        f"총 길이: {conti.total_duration_sec}초",
        f"BGM 검색어: {', '.join(conti.bgm_keywords)}",
        f"폰트: {conti.font_recommendation}",
        f"{'='*50}",
        "",
    ]

    for scene in conti.scenes:
        type_label = {
            "ai_video": "🎬 AI 영상",
            "text_overlay": "📝 텍스트",
            "screen_recording": "🖥️ 화면녹화",
        }.get(scene.scene_type, scene.scene_type)

        lines.append(f"--- 씬 {scene.scene_number} ({scene.start_sec}s ~ {scene.end_sec}s) [{type_label}] ---")
        lines.append(f"  화면: {scene.visual_description}")
        lines.append(f"  TTS: \"{scene.tts_script}\"")
        lines.append(f"  자막: \"{scene.subtitle_text}\"")
        lines.append(f"  강조: {', '.join(scene.emphasis_keywords)}")

        if scene.ai_video_prompt:
            lines.append(f"")
            lines.append(f"  🎬 AI 영상 프롬프트 (복사용):")
            lines.append(f"  ┌{'─'*48}┐")
            # 프롬프트를 줄바꿈 없이 한 블록으로
            prompt_lines = scene.ai_video_prompt.strip().split("\n")
            for pl in prompt_lines:
                lines.append(f"  │ {pl:<47}│")
            lines.append(f"  └{'─'*48}┘")

        lines.append(f"  CapCut: {scene.capcut_notes}")
        lines.append("")

    lines.append(f"{'='*50}")
    lines.append(f"📌 전체 편집 가이드")
    lines.append(f"{'='*50}")
    lines.append(conti.editing_summary)

    return "\n".join(lines)
