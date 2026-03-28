ANALYZE_VIDEO_PROMPT = """이 릴스/숏폼 영상을 분석해줘.

각 씬별로 다음을 정리해줘:
- 시작~끝 시간 (초 단위)
- 화면에 보이는 것 (인물, 배경, 구도)
- 화면 위 텍스트/자막
- 나레이션/TTS 내용
- 분위기/에너지 (긴장, 유쾌, 반전 등)
- 다음 씬으로의 전환 효과
- 얼굴 노출 여부

그리고 전체적으로:
- 훅 전략 (첫 1~3초 어떻게 시선 잡는지)
- 영상 구조 패턴 (도입-전개-반전-마무리 등)
- 예상 타겟 시청자
- 이 영상이 인기 있는 이유 분석

한국어로 답변해줘."""

ANALYZE_VIDEO_STRUCTURED_PROMPT = """이 릴스/숏폼 영상을 분석해서 JSON으로 출력해줘.

다음 JSON 스키마에 맞춰서 출력해:
{{
  "title": "영상 제목/설명",
  "total_duration_sec": 총길이(초),
  "scenes": [
    {{
      "scene_number": 1,
      "start_sec": 0.0,
      "end_sec": 3.0,
      "visual": "화면에 보이는 것 (인물, 배경, 구도)",
      "text_on_screen": "화면 위 텍스트/자막 (없으면 빈 문자열)",
      "narration": "나레이션/TTS 내용 (없으면 빈 문자열)",
      "mood": "분위기/에너지 (긴장, 유쾌, 반전 등)",
      "transition": "다음 씬으로의 전환 효과",
      "face_visible": true
    }}
  ],
  "hook_strategy": "훅 전략 - 첫 1~3초 시선 잡는 방법을 구체적으로",
  "structure_pattern": "영상 구조 패턴 (도입-전개-반전-마무리 등)",
  "target_audience": "예상 타겟 시청자",
  "viral_reason": "이 영상이 인기 있는 이유 분석 (구체적으로)",
  "bgm_style": "BGM 스타일/분위기",
  "editing_speed": "편집 속도감 (빠름/보통/느림)",
  "text_style": "자막/텍스트 스타일 (폰트, 색상, 위치 등)"
}}

한국어로 답변하되, JSON만 출력해. 다른 텍스트 없이."""

EXTRACT_PATTERNS_PROMPT = """다음은 여러 인기 숏폼 영상들의 분석 결과야.
이 영상들의 공통 패턴을 추출해서 콘텐츠 제작 가이드라인을 만들어줘.

## 분석 데이터
{analyses_json}

다음 JSON 스키마에 맞춰 출력해:
{{
  "video_count": 분석한영상수,
  "common_hook_types": ["공통 훅 유형1", "유형2"],
  "common_structure": "가장 많이 쓰인 영상 구조 패턴",
  "avg_duration_sec": 평균길이,
  "avg_scene_count": 평균씬수,
  "common_moods": ["자주 쓰이는 분위기1", "분위기2"],
  "common_transitions": ["자주 쓰이는 전환1", "전환2"],
  "face_visible_ratio": 얼굴노출비율(0~1),
  "viral_factors": ["공통 바이럴 요소1", "요소2"],
  "editing_insights": "편집 관련 종합 인사이트",
  "actionable_guidelines": [
    "실행 가능한 가이드라인 1 - 구체적으로",
    "실행 가능한 가이드라인 2 - 구체적으로",
    "실행 가능한 가이드라인 3 - 구체적으로"
  ]
}}

핵심: actionable_guidelines는 바로 따라할 수 있는 구체적 지침이어야 해.
예: "첫 1초에 충격적 숫자나 질문으로 시작" (O) vs "훅을 잘 쓰세요" (X)

한국어로, JSON만 출력해."""

GENERATE_CONTI_PROMPT = """너는 한국 숏폼 콘텐츠(릴스/숏츠) 전문 스크립트 작가이자 콘티 작성자야.

## 크리에이터 정보
- 상황: 알바생 + 개발자 + 창업 준비 중
- 채널 컨셉: 알바 썰, 과거 썰, 개발 프로젝트 자랑, 학습 내용 공유
- 스타일: 얼굴 노출 없음 (AI 영상으로 재연하거나 텍스트 오버레이)
- 편집: CapCut에서 수동 편집, CapCut TTS 사용
- 톤: 2026년 MZ세대 숏폼 말투. 과장된 리액션, 유행어 자연스럽게 섞기
- 유행어 예시 (상황에 맞게 자연스럽게 활용):
  - "쌰갈!" (가자/출발/시작할 때)
  - "나 됐어요" / "엿됐어요!!!" (망했을 때, 큰일났을 때)
  - "ㄹㅇ 미쳤거든?" (진짜 대단할 때)
  - "개쩔어" / "개쩔었음" (감탄)
  - "아 ㅋㅋ 이거 실화임?" (믿기 어려울 때)
  - "존버했더니" (버텼더니 결과가 나왔을 때)
  - "갓생 살아보겠다고" (열심히 살겠다는 다짐)
  - "뇌절인 거 알지만" (좀 오버인 거 아는데)
  - "찐이야 이건" (진짜라는 강조)
  - "역대급" (최고/최악일 때)
- 주의: 유행어를 매 문장마다 넣지 말고, 훅/반전/마무리 등 임팩트 있는 순간에만 사용
- TTS 대사는 말하듯이 자연스럽게. 글로 읽히는 게 아니라 소리로 들렸을 때 찰지게

## 입력 콘텐츠
{input_content}

## 콘텐츠 유형
{content_type}

## 출력 규칙
1. 총 길이 15~60초 (릴스 최적)
2. 첫 씬은 반드시 훅 (1~3초, 궁금증 유발하는 텍스트)
3. 마지막 씬은 CTA 포함 (팔로우/좋아요 유도)
4. scene_type 구분:
   - "text_overlay": 텍스트+배경 짤/이미지만 (나레이션 위주)
   - "ai_video": 재연이 필요한 장면 → ai_video_prompt 필수 작성
   - "screen_recording": 코드/앱 화면 보여주는 장면
5. ai_video_prompt 규칙:
   - 반드시 영어로 작성
   - "No background music, no voice, no text overlay" 항상 포함
   - 얼굴은 안 보이게: 뒷모습, 손만, 또는 먼 거리에서 촬영
   - "Cinematic, 24fps" 포함
   - Kling/Hailuo에서 바로 복붙 가능하도록 구체적으로
6. tts_script: CapCut TTS로 읽을 텍스트 (자연스러운 구어체)
7. emphasis_keywords: 자막에서 색상/크기 강조할 핵심 단어 2~3개
8. capcut_notes: 해당 씬의 전환효과, 자막 스타일, 타이밍 팁

다음 JSON 스키마에 맞춰서 출력해줘:
{{
  "title": "콘티 제목",
  "total_duration_sec": 총길이,
  "bgm_keywords": ["CapCut에서 검색할 BGM 키워드"],
  "font_recommendation": "추천 폰트",
  "scenes": [
    {{
      "scene_number": 1,
      "start_sec": 0.0,
      "end_sec": 3.0,
      "scene_type": "text_overlay | ai_video | screen_recording",
      "visual_description": "화면 설명",
      "tts_script": "TTS 대사",
      "subtitle_text": "화면 자막",
      "emphasis_keywords": ["강조1", "강조2"],
      "ai_video_prompt": "English prompt or null",
      "capcut_notes": "편집 노트"
    }}
  ],
  "editing_summary": "전체 CapCut 작업 요약"
}}

JSON만 출력해. 다른 텍스트 없이."""

GENERATE_FROM_REFERENCE_PROMPT = """너는 한국 숏폼 콘텐츠(릴스/숏츠) 전문 스크립트 작가이자 콘티 작성자야.

## 크리에이터 정보
- 상황: 알바생 + 개발자 + 창업 준비 중
- 채널 컨셉: 알바 썰, 과거 썰, 개발 프로젝트 자랑, 학습 내용 공유
- 스타일: 얼굴 노출 없음 (AI 영상으로 재연하거나 텍스트 오버레이)
- 편집: CapCut에서 수동 편집, CapCut TTS 사용
- 톤: 2026년 MZ세대 숏폼 말투. 과장된 리액션, 유행어 자연스럽게 섞기
- 유행어 예시 (상황에 맞게 자연스럽게 활용):
  - "쌰갈!" (가자/출발/시작할 때)
  - "나 됐어요" / "엿됐어요!!!" (망했을 때, 큰일났을 때)
  - "ㄹㅇ 미쳤거든?" (진짜 대단할 때)
  - "개쩔어" / "개쩔었음" (감탄)
  - "아 ㅋㅋ 이거 실화임?" (믿기 어려울 때)
  - "존버했더니" (버텼더니 결과가 나왔을 때)
  - "갓생 살아보겠다고" (열심히 살겠다는 다짐)
  - "뇌절인 거 알지만" (좀 오버인 거 아는데)
  - "찐이야 이건" (진짜라는 강조)
  - "역대급" (최고/최악일 때)
- 주의: 유행어를 매 문장마다 넣지 말고, 훅/반전/마무리 등 임팩트 있는 순간에만 사용
- TTS 대사는 말하듯이 자연스럽게. 글로 읽히는 게 아니라 소리로 들렸을 때 찰지게

## 참고 영상 분석 결과
{video_analysis}

## 내 썰/콘텐츠
{story_text}

## 콘텐츠 유형
{content_type}

## 지시사항
위 참고 영상의 구조와 패턴(훅 방식, 전개, 전환, CTA)을 모방하되,
내용은 내 썰/콘텐츠로 완전히 교체해서 새로운 콘티를 만들어줘.

## 출력 규칙
1. 총 길이 15~60초 (릴스 최적)
2. 첫 씬은 반드시 훅 (1~3초, 궁금증 유발하는 텍스트)
3. 마지막 씬은 CTA 포함 (팔로우/좋아요 유도)
4. scene_type 구분:
   - "text_overlay": 텍스트+배경 짤/이미지만 (나레이션 위주)
   - "ai_video": 재연이 필요한 장면 → ai_video_prompt 필수 작성
   - "screen_recording": 코드/앱 화면 보여주는 장면
5. ai_video_prompt 규칙:
   - 반드시 영어로 작성
   - "No background music, no voice, no text overlay" 항상 포함
   - 얼굴은 안 보이게: 뒷모습, 손만, 또는 먼 거리에서 촬영
   - "Cinematic, 24fps" 포함
   - Kling/Hailuo에서 바로 복붙 가능하도록 구체적으로
6. tts_script: CapCut TTS로 읽을 텍스트 (자연스러운 구어체)
7. emphasis_keywords: 자막에서 색상/크기 강조할 핵심 단어 2~3개
8. capcut_notes: 해당 씬의 전환효과, 자막 스타일, 타이밍 팁

다음 JSON 스키마에 맞춰서 출력해줘:
{{
  "title": "콘티 제목",
  "total_duration_sec": 총길이,
  "bgm_keywords": ["CapCut에서 검색할 BGM 키워드"],
  "font_recommendation": "추천 폰트",
  "scenes": [
    {{
      "scene_number": 1,
      "start_sec": 0.0,
      "end_sec": 3.0,
      "scene_type": "text_overlay | ai_video | screen_recording",
      "visual_description": "화면 설명",
      "tts_script": "TTS 대사",
      "subtitle_text": "화면 자막",
      "emphasis_keywords": ["강조1", "강조2"],
      "ai_video_prompt": "English prompt or null",
      "capcut_notes": "편집 노트"
    }}
  ],
  "editing_summary": "전체 CapCut 작업 요약"
}}

JSON만 출력해. 다른 텍스트 없이."""
