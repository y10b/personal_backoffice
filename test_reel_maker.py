"""릴스 콘티 생성기 테스트"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from models import Conti, Scene
from prompts import ANALYZE_VIDEO_PROMPT, GENERATE_CONTI_PROMPT, GENERATE_FROM_REFERENCE_PROMPT
from generator import _clean_json, format_conti, generate_from_story, generate_from_reference
from analyzer import analyze_video, download_reel, DOWNLOADS_DIR


# ============================================================
# models.py 테스트
# ============================================================

class TestModels:
    def test_scene_creation(self):
        """Scene 모델이 올바르게 생성되는지"""
        scene = Scene(
            scene_number=1,
            start_sec=0.0,
            end_sec=3.0,
            scene_type="text_overlay",
            visual_description="검은 배경 + 흰 텍스트",
            tts_script="",
            subtitle_text="롯데리아 첫날 잘린 뻔한 이유",
            emphasis_keywords=["첫날", "잘린"],
            capcut_notes="페이드인 효과",
        )
        assert scene.scene_number == 1
        assert scene.scene_type == "text_overlay"
        assert scene.ai_video_prompt is None  # 기본값 None

    def test_scene_with_ai_video_prompt(self):
        """AI 영상 프롬프트가 있는 Scene"""
        scene = Scene(
            scene_number=2,
            start_sec=3.0,
            end_sec=8.0,
            scene_type="ai_video",
            visual_description="감자튀김 쏟는 장면",
            tts_script="첫날부터 감자튀김을 통째로 바닥에 쏟았는데",
            subtitle_text="통째로 바닥에 쏟음",
            emphasis_keywords=["통째로"],
            ai_video_prompt="A young Asian male worker in a fast food uniform dropping a tray of french fries. No background music, no voice, no text overlay. Cinematic, 24fps.",
            capcut_notes="글리치 전환",
        )
        assert scene.ai_video_prompt is not None
        assert "No background music" in scene.ai_video_prompt

    def test_scene_invalid_type_rejected(self):
        """잘못된 scene_type은 거부되는지"""
        with pytest.raises(Exception):
            Scene(
                scene_number=1,
                start_sec=0.0,
                end_sec=3.0,
                scene_type="invalid_type",
                visual_description="test",
                tts_script="test",
                subtitle_text="test",
                emphasis_keywords=[],
                capcut_notes="test",
            )

    def test_conti_creation(self):
        """Conti 모델이 올바르게 생성되는지"""
        scene = Scene(
            scene_number=1,
            start_sec=0.0,
            end_sec=3.0,
            scene_type="text_overlay",
            visual_description="훅",
            tts_script="",
            subtitle_text="제목",
            emphasis_keywords=["제목"],
            capcut_notes="페이드인",
        )
        conti = Conti(
            title="테스트 콘티",
            total_duration_sec=30.0,
            bgm_keywords=["긴장", "밝은"],
            font_recommendation="본고딕 Bold",
            scenes=[scene],
            editing_summary="전체 요약",
        )
        assert conti.title == "테스트 콘티"
        assert len(conti.scenes) == 1
        assert conti.total_duration_sec == 30.0

    def test_conti_from_json(self):
        """JSON에서 Conti 파싱이 되는지 (Gemini 응답 시뮬레이션)"""
        json_str = json.dumps({
            "title": "감자튀김 썰",
            "total_duration_sec": 27.0,
            "bgm_keywords": ["긴장감", "따뜻한"],
            "font_recommendation": "Pretendard Bold",
            "scenes": [
                {
                    "scene_number": 1,
                    "start_sec": 0.0,
                    "end_sec": 3.0,
                    "scene_type": "text_overlay",
                    "visual_description": "검은 배경",
                    "tts_script": "",
                    "subtitle_text": "롯데리아 첫날",
                    "emphasis_keywords": ["첫날"],
                    "ai_video_prompt": None,
                    "capcut_notes": "페이드인",
                },
                {
                    "scene_number": 2,
                    "start_sec": 3.0,
                    "end_sec": 8.0,
                    "scene_type": "ai_video",
                    "visual_description": "감자튀김 쏟는 장면",
                    "tts_script": "첫날부터 감자튀김을 통째로 쏟았는데",
                    "subtitle_text": "통째로 쏟음",
                    "emphasis_keywords": ["통째로"],
                    "ai_video_prompt": "A worker dropping fries. No background music, no voice, no text overlay. Cinematic, 24fps.",
                    "capcut_notes": "글리치",
                },
            ],
            "editing_summary": "편집 가이드",
        })
        conti = Conti.model_validate_json(json_str)
        assert conti.title == "감자튀김 썰"
        assert len(conti.scenes) == 2
        assert conti.scenes[0].ai_video_prompt is None
        assert conti.scenes[1].ai_video_prompt is not None


# ============================================================
# prompts.py 테스트
# ============================================================

class TestPrompts:
    def test_analyze_prompt_exists(self):
        """분석 프롬프트가 비어있지 않은지"""
        assert len(ANALYZE_VIDEO_PROMPT) > 100

    def test_generate_prompt_has_placeholders(self):
        """생성 프롬프트에 필요한 플레이스홀더가 있는지"""
        assert "{input_content}" in GENERATE_CONTI_PROMPT
        assert "{content_type}" in GENERATE_CONTI_PROMPT

    def test_reference_prompt_has_placeholders(self):
        """참고 영상 프롬프트에 필요한 플레이스홀더가 있는지"""
        assert "{video_analysis}" in GENERATE_FROM_REFERENCE_PROMPT
        assert "{story_text}" in GENERATE_FROM_REFERENCE_PROMPT
        assert "{content_type}" in GENERATE_FROM_REFERENCE_PROMPT

    def test_generate_prompt_format(self):
        """프롬프트 포맷팅이 정상 동작하는지"""
        formatted = GENERATE_CONTI_PROMPT.format(
            input_content="테스트 썰",
            content_type="알바 썰",
        )
        assert "테스트 썰" in formatted
        assert "알바 썰" in formatted
        assert "{input_content}" not in formatted

    def test_reference_prompt_format(self):
        """참고 영상 프롬프트 포맷팅"""
        formatted = GENERATE_FROM_REFERENCE_PROMPT.format(
            video_analysis="분석 결과 텍스트",
            story_text="내 썰 텍스트",
            content_type="개발 자랑",
        )
        assert "분석 결과 텍스트" in formatted
        assert "내 썰 텍스트" in formatted
        assert "개발 자랑" in formatted

    def test_prompt_contains_persona(self):
        """프롬프트에 재현 페르소나가 포함되어 있는지"""
        assert "재현" in GENERATE_CONTI_PROMPT
        assert "롯데리아" in GENERATE_CONTI_PROMPT
        assert "얼굴 노출 없음" in GENERATE_CONTI_PROMPT

    def test_prompt_contains_ai_video_rules(self):
        """AI 영상 프롬프트 규칙이 포함되어 있는지"""
        assert "No background music" in GENERATE_CONTI_PROMPT
        assert "영어로 작성" in GENERATE_CONTI_PROMPT
        assert "Cinematic" in GENERATE_CONTI_PROMPT


# ============================================================
# generator.py 테스트
# ============================================================

class TestCleanJson:
    def test_plain_json(self):
        """순수 JSON은 그대로 반환"""
        raw = '{"title": "test"}'
        assert _clean_json(raw) == '{"title": "test"}'

    def test_markdown_wrapped_json(self):
        """마크다운 코드블록 안의 JSON 추출"""
        raw = '```json\n{"title": "test"}\n```'
        assert _clean_json(raw) == '{"title": "test"}'

    def test_markdown_without_lang(self):
        """언어 표시 없는 코드블록"""
        raw = '```\n{"title": "test"}\n```'
        assert _clean_json(raw) == '{"title": "test"}'

    def test_with_surrounding_text(self):
        """코드블록 앞뒤 텍스트가 있는 경우"""
        raw = '여기 결과입니다:\n```json\n{"title": "test"}\n```\n끝.'
        assert _clean_json(raw) == '{"title": "test"}'


SAMPLE_CONTI_JSON = json.dumps({
    "title": "감자튀김 쏟은 썰",
    "total_duration_sec": 27.0,
    "bgm_keywords": ["긴장감"],
    "font_recommendation": "Pretendard Bold",
    "scenes": [
        {
            "scene_number": 1,
            "start_sec": 0.0,
            "end_sec": 3.0,
            "scene_type": "text_overlay",
            "visual_description": "검은 배경 + 흰 텍스트",
            "tts_script": "",
            "subtitle_text": "롯데리아 첫날 잘린 뻔한 이유",
            "emphasis_keywords": ["첫날", "잘린"],
            "ai_video_prompt": None,
            "capcut_notes": "페이드인",
        },
        {
            "scene_number": 2,
            "start_sec": 3.0,
            "end_sec": 8.0,
            "scene_type": "ai_video",
            "visual_description": "감자튀김 쏟는 장면 재연",
            "tts_script": "첫날부터 감자튀김을 통째로 바닥에 쏟았는데",
            "subtitle_text": "감자튀김을 통째로 쏟음",
            "emphasis_keywords": ["통째로"],
            "ai_video_prompt": "A young Asian male worker in a fast food restaurant uniform carrying a tray of french fries. The tray slips and fries scatter on the floor. Shot from behind, face not visible. No background music, no voice, no text overlay. Cinematic, 24fps.",
            "capcut_notes": "글리치 전환",
        },
    ],
    "editing_summary": "전체 편집 가이드 내용",
}, ensure_ascii=False)


class TestFormatConti:
    def test_format_basic(self):
        """포맷 출력이 정상적으로 되는지"""
        conti = Conti.model_validate_json(SAMPLE_CONTI_JSON)
        output = format_conti(conti)

        assert "감자튀김 쏟은 썰" in output
        assert "27.0초" in output
        assert "씬 1" in output
        assert "씬 2" in output
        assert "📝 텍스트" in output
        assert "🎬 AI 영상" in output

    def test_format_contains_ai_prompt(self):
        """AI 영상 프롬프트가 출력에 포함되는지"""
        conti = Conti.model_validate_json(SAMPLE_CONTI_JSON)
        output = format_conti(conti)

        assert "복사용" in output
        assert "No background music" in output

    def test_format_no_ai_prompt_for_text_overlay(self):
        """text_overlay 씬에는 AI 프롬프트 섹션이 없는지"""
        conti_json = json.dumps({
            "title": "테스트",
            "total_duration_sec": 10.0,
            "bgm_keywords": [],
            "font_recommendation": "test",
            "scenes": [
                {
                    "scene_number": 1,
                    "start_sec": 0.0,
                    "end_sec": 3.0,
                    "scene_type": "text_overlay",
                    "visual_description": "텍스트만",
                    "tts_script": "TTS",
                    "subtitle_text": "자막",
                    "emphasis_keywords": [],
                    "ai_video_prompt": None,
                    "capcut_notes": "없음",
                }
            ],
            "editing_summary": "요약",
        })
        conti = Conti.model_validate_json(conti_json)
        output = format_conti(conti)

        # text_overlay 씬에는 AI 프롬프트 블록이 없어야 함
        assert "복사용" not in output


class TestGenerateFromStory:
    def test_calls_gemini_and_returns_conti(self):
        """Gemini API를 호출하고 Conti를 반환하는지"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_CONTI_JSON
        mock_client.models.generate_content.return_value = mock_response

        conti = generate_from_story("감자튀김 쏟은 썰", "알바 썰", mock_client)

        assert isinstance(conti, Conti)
        assert conti.title == "감자튀김 쏟은 썰"
        assert len(conti.scenes) == 2
        mock_client.models.generate_content.assert_called_once()

    def test_prompt_contains_story_text(self):
        """Gemini에 전달되는 프롬프트에 썰 내용이 포함되는지"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_CONTI_JSON
        mock_client.models.generate_content.return_value = mock_response

        generate_from_story("나만의 특별한 썰", "과거 썰", mock_client)

        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", call_args.args[0] if call_args.args else None)
        if isinstance(prompt, list):
            prompt = prompt[0]
        assert "나만의 특별한 썰" in str(prompt)


class TestGenerateFromReference:
    def test_calls_gemini_with_analysis(self):
        """참고 영상 분석 결과가 프롬프트에 포함되는지"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_CONTI_JSON
        mock_client.models.generate_content.return_value = mock_response

        conti = generate_from_reference(
            "영상 분석 결과: 훅이 강력함",
            "내 썰 내용",
            "알바 썰",
            mock_client,
        )

        assert isinstance(conti, Conti)
        call_args = mock_client.models.generate_content.call_args
        prompt_str = str(call_args)
        assert "영상 분석 결과" in prompt_str


# ============================================================
# analyzer.py 테스트
# ============================================================

class TestDownloadReel:
    def test_download_failure_shows_helpful_message(self):
        """다운로드 실패 시 친절한 에러 메시지"""
        with pytest.raises(RuntimeError, match="직접 다운로드"):
            download_reel("https://www.instagram.com/reel/FAKE_URL_12345/")

    def test_downloads_dir_constant(self):
        """다운로드 디렉토리가 올바르게 설정되어 있는지"""
        assert DOWNLOADS_DIR.name == "downloads"
        assert DOWNLOADS_DIR.parent == Path(__file__).parent


class TestAnalyzeVideo:
    def test_analyze_calls_gemini(self):
        """영상 분석이 Gemini API를 올바르게 호출하는지"""
        mock_client = MagicMock()

        # files.upload mock
        mock_file = MagicMock()
        mock_file.state.name = "ACTIVE"  # 바로 처리 완료
        mock_file.name = "test_file"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file

        # generate_content mock
        mock_response = MagicMock()
        mock_response.text = "분석 결과: 훅이 강력하고 전환이 빠름"
        mock_client.models.generate_content.return_value = mock_response

        # 임시 파일 생성
        test_file = DOWNLOADS_DIR / "test_video.mp4"
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        test_file.write_bytes(b"fake video content")

        try:
            result = analyze_video(test_file, mock_client)

            assert result == "분석 결과: 훅이 강력하고 전환이 빠름"
            mock_client.files.upload.assert_called_once()
            mock_client.models.generate_content.assert_called_once()
        finally:
            test_file.unlink(missing_ok=True)

    def test_analyze_waits_for_processing(self):
        """영상 처리 대기 로직이 동작하는지"""
        mock_client = MagicMock()

        # 처음엔 PROCESSING, 두 번째에 ACTIVE
        mock_file_processing = MagicMock()
        mock_file_processing.state.name = "PROCESSING"
        mock_file_processing.name = "test_file"

        mock_file_active = MagicMock()
        mock_file_active.state.name = "ACTIVE"
        mock_file_active.name = "test_file"

        mock_client.files.upload.return_value = mock_file_processing
        mock_client.files.get.return_value = mock_file_active

        mock_response = MagicMock()
        mock_response.text = "분석 완료"
        mock_client.models.generate_content.return_value = mock_response

        test_file = DOWNLOADS_DIR / "test_video2.mp4"
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        test_file.write_bytes(b"fake")

        try:
            with patch("analyzer.time.sleep"):  # sleep 건너뛰기
                result = analyze_video(test_file, mock_client)
            assert result == "분석 완료"
        finally:
            test_file.unlink(missing_ok=True)


# ============================================================
# main.py CLI 테스트
# ============================================================

def _run_cli(*args, **env_overrides):
    """Windows cp949 이슈를 우회해서 CLI 실행"""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "main.py", *args],
        capture_output=True,
        cwd=str(Path(__file__).parent),
        env=env,
        encoding="utf-8",
        errors="replace",
    )


class TestCLI:
    def test_no_args_shows_help(self):
        """인자 없이 실행하면 에러 (mode 필수)"""
        result = _run_cli()
        assert result.returncode != 0

    def test_story_mode_no_api_key(self):
        """API 키 없으면 안내 메시지 출력"""
        result = _run_cli("story", "테스트 썰", GEMINI_API_KEY="")
        output = result.stdout + result.stderr
        assert "GEMINI_API_KEY" in output or result.returncode != 0

    def test_help_flag(self):
        """--help 플래그 동작"""
        result = _run_cli("--help")
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_story_subcommand_help(self):
        """story 서브커맨드 help"""
        result = _run_cli("story", "--help")
        assert result.returncode == 0

    def test_url_subcommand_help(self):
        """url 서브커맨드 help"""
        result = _run_cli("url", "--help")
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
