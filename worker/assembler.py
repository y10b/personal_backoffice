"""FFmpeg 영상 조립기 — 씬 이미지 + TTS → 영상."""

import json
import subprocess
from pathlib import Path

from mutagen.mp3 import MP3


def get_mp3_duration(mp3_path: Path) -> float:
    """MP3 파일 길이(초) 반환."""
    audio = MP3(str(mp3_path))
    return audio.info.length


def assemble_scene(image_path: Path, audio_path: Path | None, duration: float, output_path: Path):
    """단일 씬: 이미지 + 오디오 → 영상 클립."""
    if audio_path and audio_path.exists():
        # TTS 오디오 길이를 씬 길이로 사용
        actual_duration = get_mp3_duration(audio_path)
        duration = max(duration, actual_duration + 0.3)  # 여유 0.3초

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-shortest",
            str(output_path),
        ]
    else:
        # 오디오 없는 씬 (짧은 텍스트만)
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-an",
            str(output_path),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 씬 조립 실패: {result.stderr[:500]}")


def concat_scenes(scene_videos: list[Path], output_path: Path):
    """여러 씬 영상을 이어붙이기."""
    # concat 파일 생성
    concat_file = output_path.parent / "concat.txt"
    with open(concat_file, "w") as f:
        for v in scene_videos:
            f.write(f"file '{v}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg concat 실패: {result.stderr[:500]}")


def assemble_video(conti_json: str, images_dir: Path, tts_dir: Path, output_path: Path) -> Path:
    """콘티 JSON + 이미지 + TTS → 완성 영상.

    Returns: output_path
    """
    data = json.loads(conti_json)
    scenes = data.get("scenes", [])

    work_dir = output_path.parent / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    scene_videos = []

    for scene in scenes:
        num = scene.get("scene_number", 0)
        start = scene.get("start_sec", 0)
        end = scene.get("end_sec", 3)
        duration = end - start

        # 이미지 찾기
        image_path = None
        for ext in ["png", "jpg"]:
            candidate = images_dir / f"scene_{num:02d}.{ext}"
            if candidate.exists():
                image_path = candidate
                break
            candidate = images_dir / f"scene_{num:02d}_placeholder.{ext}"
            if candidate.exists():
                image_path = candidate
                break

        if not image_path:
            continue

        # TTS 찾기
        tts_path = tts_dir / f"scene_{num:02d}.mp3"
        if not tts_path.exists():
            tts_path = None

        # 씬 영상 생성
        scene_output = work_dir / f"scene_{num:02d}.mp4"
        assemble_scene(image_path, tts_path, duration, scene_output)
        scene_videos.append(scene_output)

    if not scene_videos:
        raise RuntimeError("조립할 씬이 없습니다.")

    # 이어붙이기
    concat_scenes(scene_videos, output_path)

    # 작업 파일 정리
    for v in scene_videos:
        v.unlink(missing_ok=True)
    work_dir.rmdir()

    return output_path
