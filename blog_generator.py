from __future__ import annotations

import json
import re

from google import genai
from google.genai.types import GenerateContentConfig

from blog_prompts import BLOG_DEV_PROMPT, BLOG_HIGH_CPC_PROMPT, BLOG_KEYWORD_PROMPT
from models import BlogPost


def _clean_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def suggest_keywords(
    blog_type: str, topic_hint: str, client: genai.Client
) -> list[dict]:
    """키워드 추천 (검색량/난이도 기반)."""
    if blog_type == "dev":
        extra = "개발자/IT 종사자가 검색하는 키워드"
        type_desc = "개발 블로그 (프로그래밍, 개발 도구, 창업, 프로젝트)"
    else:
        extra = "광고 단가(CPC)가 높은 청년 지원금/프리랜서 세금/N잡 경제/대출·금융상품/보험/청년 주거 키워드"
        type_desc = "청년 N잡러·프리랜서 경제 정보 블로그 (청년 정책, 세금, 대출, 보험, 부업 수익)"

    prompt = BLOG_KEYWORD_PROMPT.format(
        blog_type=type_desc,
        topic_hint=topic_hint or "이번 주 트렌드에 맞는 키워드 추천",
        extra_condition=extra,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=GenerateContentConfig(response_mime_type="application/json"),
    )

    return json.loads(_clean_json(response.text))


def generate_dev_post(
    keyword: str, context: str, client: genai.Client
) -> BlogPost:
    """개발 블로그 글 생성."""
    prompt = BLOG_DEV_PROMPT.format(keyword=keyword, context=context)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=GenerateContentConfig(response_mime_type="application/json"),
    )

    raw = _clean_json(response.text)
    return BlogPost.model_validate_json(raw)


def generate_high_cpc_post(
    keyword: str, cpc_category: str, context: str, client: genai.Client
) -> BlogPost:
    """고단가 CPC 블로그 글 생성."""
    prompt = BLOG_HIGH_CPC_PROMPT.format(
        keyword=keyword,
        cpc_category=cpc_category,
        context=context,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=GenerateContentConfig(response_mime_type="application/json"),
    )

    raw = _clean_json(response.text)
    return BlogPost.model_validate_json(raw)


def format_blog_post(post: BlogPost) -> str:
    """BlogPost를 읽기 좋은 텍스트로 포맷한다."""
    lines = [
        f"{'='*50}",
        f"📝 {post.title}",
        f"{'='*50}",
        f"URL: /{post.slug}",
        f"카테고리: {post.category}",
        f"키워드: {', '.join(post.keywords)}",
        f"태그: {', '.join(post.tags)}",
        f"읽기 시간: {post.estimated_reading_min}분",
    ]
    if post.cpc_category:
        lines.append(f"CPC 카테고리: {post.cpc_category}")

    lines.append(f"\n📋 메타 디스크립션:\n{post.meta_description}")
    lines.append(f"\n{'─'*50}")
    lines.append("📄 본문 (HTML):")
    lines.append(f"{'─'*50}")
    lines.append(post.html_content)

    if post.images:
        lines.append(f"\n{'─'*50}")
        lines.append("🖼️ 필요한 이미지:")
        lines.append(f"{'─'*50}")
        for i, img in enumerate(post.images, 1):
            lines.append(f"\n  [{i}] 위치: {img.position}")
            lines.append(f"      Alt: {img.alt_text}")
            lines.append(f"      프롬프트: {img.prompt}")

    return "\n".join(lines)
