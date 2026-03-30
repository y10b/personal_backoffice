"""Edge TTS 모듈 — 숏폼 스타일 SSML 생성 + MP3 변환."""

import asyncio
import re
from pathlib import Path

import edge_tts

# 한국어 음성 옵션
VOICES = {
    "female": "ko-KR-SunHiNeural",    # 여성, 자연스러움
    "male": "ko-KR-InJoonNeural",      # 남성
    "male_expressive": "ko-KR-HyunsuNeural",  # 남성, 감정 표현
}

DEFAULT_VOICE = VOICES["female"]
DEFAULT_RATE = "+12%"  # 숏폼은 살짝 빠르게


def text_to_ssml(text: str, rate: str = DEFAULT_RATE) -> str:
    """TTS 텍스트를 숏폼 스타일 SSML로 변환.

    자동 처리:
    - "..." → 500ms 멈춤 (극적 멈춤)
    - "근데요," "아니" 뒤 → 짧은 멈춤
    - 전체 속도 약간 빠르게
    """
    # 특수 멈춤 처리
    text = re.sub(r'\.{3,}', '<break time="500ms"/>', text)
    text = re.sub(r'([근데요,|아니,|그래서,|진짜,])\s', r'\1<break time="300ms"/> ', text)

    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">
    <voice name="{DEFAULT_VOICE}">
        <prosody rate="{rate}">
            {text}
        </prosody>
    </voice>
</speak>"""
    return ssml


async def _generate_tts(text: str, output_path: Path, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE):
    """Edge TTS로 MP3 생성."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))


def generate_scene_tts(tts_script: str, output_path: Path, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE):
    """동기 래퍼 — 씬의 TTS 스크립트를 MP3로 변환."""
    asyncio.run(_generate_tts(tts_script, output_path, voice, rate))
    return output_path


def generate_all_scene_tts(scenes: list[dict], output_dir: Path, voice: str = DEFAULT_VOICE) -> list[Path]:
    """콘티의 모든 씬 TTS를 생성."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    for scene in scenes:
        tts_text = scene.get("tts_script", "")
        if not tts_text:
            paths.append(None)
            continue

        scene_num = scene.get("scene_number", 0)
        output_path = output_dir / f"scene_{scene_num:02d}.mp3"
        generate_scene_tts(tts_text, output_path, voice)
        paths.append(output_path)

    return paths
