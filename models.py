from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ── 영상 분석 모델 ──


class AnalyzedScene(BaseModel):
    """분석된 개별 씬"""
    scene_number: int
    start_sec: float
    end_sec: float
    visual: str = Field(description="화면에 보이는 것 (인물, 배경, 구도)")
    text_on_screen: str = Field(description="화면 위 텍스트/자막")
    narration: str = Field(description="나레이션/TTS 내용")
    mood: str = Field(description="분위기/에너지 (긴장, 유쾌, 반전 등)")
    transition: str = Field(description="다음 씬으로의 전환 효과")
    face_visible: bool = Field(description="얼굴 노출 여부")


class VideoAnalysis(BaseModel):
    """단일 영상 분석 결과 (구조화)"""
    url: str = ""
    title: str = Field(description="영상 제목/설명")
    total_duration_sec: float
    scenes: list[AnalyzedScene]

    # 전체 분석
    hook_strategy: str = Field(description="훅 전략 - 첫 1~3초 시선 잡는 방법")
    structure_pattern: str = Field(description="영상 구조 패턴 (도입-전개-반전-마무리 등)")
    target_audience: str = Field(description="예상 타겟 시청자")
    viral_reason: str = Field(description="이 영상이 인기 있는 이유")

    # 기술적 요소
    bgm_style: str = Field(default="", description="BGM 스타일/분위기")
    editing_speed: str = Field(default="", description="편집 속도감 (빠름/보통/느림)")
    text_style: str = Field(default="", description="자막/텍스트 스타일")


class PatternReport(BaseModel):
    """여러 영상 분석에서 추출한 공통 패턴"""
    video_count: int
    common_hook_types: list[str] = Field(description="공통 훅 유형들")
    common_structure: str = Field(description="가장 많이 쓰인 영상 구조")
    avg_duration_sec: float
    avg_scene_count: float
    common_moods: list[str] = Field(description="자주 쓰이는 분위기/에너지")
    common_transitions: list[str] = Field(description="자주 쓰이는 전환 효과")
    face_visible_ratio: float = Field(description="얼굴 노출 비율 (0~1)")
    viral_factors: list[str] = Field(description="공통 바이럴 요소")
    editing_insights: str = Field(description="편집 관련 인사이트")
    actionable_guidelines: list[str] = Field(description="실행 가능한 가이드라인")


# ── 블로그 모델 ──


class BlogImage(BaseModel):
    """블로그 본문에 삽입할 이미지"""
    position: str = Field(description="이미지 삽입 위치 (어떤 섹션 아래)")
    alt_text: str = Field(description="이미지 alt 텍스트 (SEO용)")
    prompt: str = Field(description="이미지 생성 프롬프트 (영어, DALL-E/Midjourney용)")


class BlogPost(BaseModel):
    """SEO 최적화된 블로그 글"""
    # SEO 메타
    title: str = Field(description="SEO 최적화 제목 (32자 내외)")
    meta_description: str = Field(description="메타 디스크립션 (155자 내외)")
    keywords: list[str] = Field(description="타겟 키워드 (메인 1개 + 서브 3~5개)")
    slug: str = Field(description="URL 슬러그 (영문)")
    category: str = Field(description="카테고리")
    tags: list[str] = Field(description="태그 (5~10개)")

    # 본문
    html_content: str = Field(description="HTML 본문 (H2/H3 구조, SEO 최적화)")

    # 이미지
    images: list[BlogImage] = Field(default=[], description="필요한 이미지 목록")

    # 부가 정보
    estimated_reading_min: int = Field(description="예상 읽기 시간 (분)")
    cpc_category: str = Field(default="", description="CPC 카테고리 (고단가 블로그용)")


# ── 콘티 생성 모델 ──


class Scene(BaseModel):
    scene_number: int
    start_sec: float
    end_sec: float
    scene_type: Literal["ai_video", "text_overlay", "screen_recording"]
    visual_description: str
    tts_script: str
    subtitle_text: str
    emphasis_keywords: list[str]
    ai_video_prompt: str | None = None
    capcut_notes: str


class Conti(BaseModel):
    title: str
    total_duration_sec: float
    bgm_keywords: list[str]
    font_recommendation: str
    scenes: list[Scene]
    editing_summary: str
