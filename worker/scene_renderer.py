"""씬 이미지 생성기 — text_overlay 씬을 이미지로 렌더링."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 숏폼 세로 (9:16)
WIDTH = 1080
HEIGHT = 1920
BG_COLOR = (15, 15, 20)

# 색상 팔레트
COLORS = {
    "긴장": [(30, 10, 40), (139, 92, 246)],
    "유쾌": [(10, 30, 20), (52, 211, 153)],
    "반전": [(40, 10, 10), (248, 113, 113)],
    "기본": [(15, 15, 25), (165, 180, 252)],
    "슬픔": [(10, 15, 30), (96, 165, 250)],
    "분노": [(40, 10, 10), (239, 68, 68)],
}


def get_font(size: int, bold: bool = False):
    """시스템 폰트 로드 (한글 지원)."""
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansKR-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """텍스트를 지정 너비에 맞게 줄바꿈."""
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            test = current + char
            bbox = font.getbbox(test)
            if bbox[2] > max_width:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def render_text_scene(
    subtitle_text: str,
    emphasis_keywords: list[str] = None,
    mood: str = "기본",
    scene_number: int = 1,
    output_path: Path = None,
) -> Path:
    """text_overlay 씬을 세로(9:16) 이미지로 렌더링."""
    emphasis_keywords = emphasis_keywords or []

    # 배경색 + 강조색
    colors = COLORS.get(mood, COLORS["기본"])
    bg_color = colors[0]
    accent_color = colors[1]

    img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    # 배경 그라데이션 효과 (상단)
    for y in range(HEIGHT // 3):
        alpha = y / (HEIGHT // 3)
        r = int(bg_color[0] + (bg_color[0] * 0.3) * (1 - alpha))
        g = int(bg_color[1] + (bg_color[1] * 0.3) * (1 - alpha))
        b = int(bg_color[2] + (bg_color[2] * 0.3) * (1 - alpha))
        draw.line([(0, y), (WIDTH, y)], fill=(min(r, 255), min(g, 255), min(b, 255)))

    # 메인 자막 텍스트
    font_main = get_font(72, bold=True)
    lines = wrap_text(subtitle_text, font_main, WIDTH - 120)

    # 텍스트 영역 높이 계산
    line_height = 95
    total_height = len(lines) * line_height
    start_y = (HEIGHT - total_height) // 2

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = font_main.getbbox(line)
        x = (WIDTH - bbox[2]) // 2

        # 강조 키워드 확인
        is_emphasis = any(kw in line for kw in emphasis_keywords)

        if is_emphasis:
            # 강조 배경
            padding = 16
            draw.rounded_rectangle(
                [x - padding, y - padding // 2, x + bbox[2] + padding, y + line_height - padding // 2],
                radius=12,
                fill=(accent_color[0] // 4, accent_color[1] // 4, accent_color[2] // 4),
            )
            draw.text((x, y), line, font=font_main, fill=accent_color)
        else:
            # 그림자
            draw.text((x + 2, y + 2), line, font=font_main, fill=(0, 0, 0))
            draw.text((x, y), line, font=font_main, fill=(240, 240, 240))

    # 씬 번호 (좌상단)
    font_small = get_font(28)
    draw.text((40, 40), f"SCENE {scene_number}", font=font_small, fill=(100, 100, 120))

    if output_path is None:
        output_path = Path(f"/tmp/scene_{scene_number:02d}.png")

    img.save(output_path, "PNG")
    return output_path


def render_all_scenes(scenes: list[dict], output_dir: Path) -> list[Path | None]:
    """콘티의 text_overlay 씬만 이미지 생성."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    for scene in scenes:
        scene_type = scene.get("scene_type", "")
        scene_num = scene.get("scene_number", 0)

        if scene_type == "text_overlay":
            path = render_text_scene(
                subtitle_text=scene.get("subtitle_text", ""),
                emphasis_keywords=scene.get("emphasis_keywords", []),
                mood="기본",
                scene_number=scene_num,
                output_path=output_dir / f"scene_{scene_num:02d}.png",
            )
            paths.append(path)
        else:
            # ai_video, screen_recording → placeholder 이미지
            img = Image.new("RGB", (WIDTH, HEIGHT), (20, 20, 30))
            draw = ImageDraw.Draw(img)
            font = get_font(48)
            label = "AI 영상 필요" if scene_type == "ai_video" else "화면 녹화 필요"
            bbox = font.getbbox(label)
            draw.text(((WIDTH - bbox[2]) // 2, HEIGHT // 2), label, font=font, fill=(100, 100, 120))
            path = output_dir / f"scene_{scene_num:02d}_placeholder.png"
            img.save(path)
            paths.append(path)

    return paths
