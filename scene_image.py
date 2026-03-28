"""텍스트 오버레이 씬의 미리보기 이미지를 생성한다."""

from __future__ import annotations

import re
import textwrap
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 릴스 세로 비율 (9:16)
WIDTH = 1080
HEIGHT = 1920

# 폰트 경로 (Windows)
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_REGULAR = "C:/Windows/Fonts/malgun.ttf"

# 배경 프리셋
BG_PRESETS = {
    "긴장": {"bg": "#CC0000", "text": "#FFFFFF", "accent": "#FFD700"},
    "밝은": {"bg": "#FFF8E1", "text": "#333333", "accent": "#FF6F00"},
    "어두운": {"bg": "#0A0A0A", "text": "#FFFFFF", "accent": "#7C6EF0"},
    "따뜻한": {"bg": "#FFF3E0", "text": "#4E342E", "accent": "#FF7043"},
    "차가운": {"bg": "#E3F2FD", "text": "#1A237E", "accent": "#2196F3"},
    "반전":  {"bg": "#1A1A2E", "text": "#E0E0E0", "accent": "#00E676"},
    "default": {"bg": "#0A0A0A", "text": "#FFFFFF", "accent": "#7C6EF0"},
}


def _pick_preset(visual_desc: str, capcut_notes: str) -> dict:
    """화면 설명에서 분위기를 감지해 배경 프리셋을 선택한다."""
    combined = (visual_desc + " " + capcut_notes).lower()

    # 색상이 직접 언급된 경우
    if any(w in combined for w in ["붉은", "빨간", "빨강", "레드", "긴장", "강렬", "경고", "🚨"]):
        return BG_PRESETS["긴장"]
    if any(w in combined for w in ["밝은", "밝고", "유쾌", "밝은 톤"]):
        return BG_PRESETS["밝은"]
    if any(w in combined for w in ["따뜻", "따듯", "훈훈", "감동"]):
        return BG_PRESETS["따뜻"]
    if any(w in combined for w in ["차가", "시원", "쿨"]):
        return BG_PRESETS["차가운"]
    if any(w in combined for w in ["반전", "전환"]):
        return BG_PRESETS["반전"]
    if any(w in combined for w in ["검은", "어두", "다크", "블랙"]):
        return BG_PRESETS["어두운"]

    return BG_PRESETS["default"]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """텍스트를 이미지 너비에 맞게 줄바꿈한다."""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        # 글자 수 기반 대략적 줄바꿈 후 조정
        avg_char_width = font.getbbox("가")[2]
        chars_per_line = max(1, int(max_width / avg_char_width))
        wrapped = textwrap.wrap(paragraph, width=chars_per_line)
        lines.extend(wrapped if wrapped else [""])
    return lines


def generate_scene_image(
    subtitle_text: str,
    emphasis_keywords: list[str],
    visual_description: str,
    capcut_notes: str,
    scene_number: int,
) -> bytes:
    """텍스트 오버레이 씬의 이미지를 생성하고 PNG 바이트를 반환한다."""

    preset = _pick_preset(visual_description, capcut_notes)
    bg_color = _hex_to_rgb(preset["bg"])
    text_color = _hex_to_rgb(preset["text"])
    accent_color = _hex_to_rgb(preset["accent"])

    img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    # 폰트
    try:
        font_main = ImageFont.truetype(FONT_BOLD, 72)
        font_sub = ImageFont.truetype(FONT_REGULAR, 40)
    except OSError:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # 장식: 상단/하단 바
    bar_height = 8
    draw.rectangle([0, 0, WIDTH, bar_height], fill=accent_color)
    draw.rectangle([0, HEIGHT - bar_height, WIDTH, HEIGHT], fill=accent_color)

    # 씬 번호 뱃지 (좌상단)
    badge_text = f"SCENE {scene_number}"
    try:
        font_badge = ImageFont.truetype(FONT_BOLD, 32)
    except OSError:
        font_badge = font_sub
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w = badge_bbox[2] - badge_bbox[0] + 30
    badge_h = badge_bbox[3] - badge_bbox[1] + 16
    draw.rounded_rectangle(
        [40, 60, 40 + badge_w, 60 + badge_h],
        radius=8,
        fill=accent_color,
    )
    draw.text((55, 65), badge_text, fill=bg_color, font=font_badge)

    # 메인 자막 텍스트 (중앙)
    padding = 80
    max_text_width = WIDTH - padding * 2
    lines = _wrap_text(subtitle_text, font_main, max_text_width)

    # 전체 텍스트 높이 계산
    line_height = 100
    total_text_height = len(lines) * line_height
    start_y = (HEIGHT - total_text_height) // 2

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_main)
        line_width = bbox[2] - bbox[0]
        x = (WIDTH - line_width) // 2

        # 강조 키워드 확인
        has_emphasis = any(kw in line for kw in emphasis_keywords)

        if has_emphasis:
            # 강조 배경 박스
            box_padding = 12
            draw.rounded_rectangle(
                [x - box_padding, y - box_padding,
                 x + line_width + box_padding, y + (bbox[3] - bbox[1]) + box_padding],
                radius=8,
                fill=accent_color,
            )
            draw.text((x, y), line, fill=bg_color, font=font_main)
        else:
            # 텍스트 그림자
            draw.text((x + 3, y + 3), line, fill=(0, 0, 0), font=font_main)
            draw.text((x, y), line, fill=text_color, font=font_main)

    # 하단 워터마크
    watermark = "재현 | 릴스 콘티"
    wm_bbox = draw.textbbox((0, 0), watermark, font=font_sub)
    wm_x = (WIDTH - (wm_bbox[2] - wm_bbox[0])) // 2
    draw.text((wm_x, HEIGHT - 120), watermark, fill=(*text_color[:2], min(text_color[2], 128)), font=font_sub)

    # PNG로 변환
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
