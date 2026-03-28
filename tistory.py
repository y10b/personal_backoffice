"""티스토리 API 연동 모듈.

사전 준비:
1. https://www.tistory.com/guide/api/manage/register 에서 앱 등록
2. Callback URL: http://localhost:8000/callback/tistory
3. .env에 추가:
   TISTORY_APP_ID=앱_ID
   TISTORY_SECRET_KEY=시크릿_키
   TISTORY_ACCESS_TOKEN=액세스_토큰 (아래 인증 과정 후 발급)
   TISTORY_BLOG_DEV=개발블로그주소.tistory.com
   TISTORY_BLOG_CPC=고단가블로그주소.tistory.com
"""

from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx

from models import BlogPost

TISTORY_API = "https://www.tistory.com/apis"


def get_auth_url() -> str:
    """티스토리 OAuth 인증 URL을 반환한다."""
    app_id = os.getenv("TISTORY_APP_ID", "")
    params = {
        "client_id": app_id,
        "redirect_uri": "http://localhost:8000/callback/tistory",
        "response_type": "code",
    }
    return f"https://www.tistory.com/oauth/authorize?{urlencode(params)}"


def exchange_token(code: str) -> str:
    """인증 코드를 액세스 토큰으로 교환한다."""
    resp = httpx.get(
        "https://www.tistory.com/oauth/access_token",
        params={
            "client_id": os.getenv("TISTORY_APP_ID", ""),
            "client_secret": os.getenv("TISTORY_SECRET_KEY", ""),
            "redirect_uri": "http://localhost:8000/callback/tistory",
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    # 응답: access_token=TOKEN
    return resp.text.split("=", 1)[1]


def _get_token() -> str:
    token = os.getenv("TISTORY_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError(
            "TISTORY_ACCESS_TOKEN이 설정되지 않았습니다.\n"
            "  1. python -c \"from tistory import get_auth_url; print(get_auth_url())\"\n"
            "  2. 브라우저에서 URL 열고 인증\n"
            "  3. 콜백으로 받은 code로 토큰 교환\n"
            "  4. .env에 TISTORY_ACCESS_TOKEN=토큰 추가"
        )
    return token


def post_to_tistory(
    post: BlogPost,
    blog_name: str,
    visibility: int = 3,
) -> dict:
    """티스토리에 글을 발행한다.

    Args:
        post: BlogPost 객체
        blog_name: 블로그 이름 (xxx.tistory.com의 xxx 부분)
        visibility: 0=비공개, 1=보호, 3=공개
    Returns:
        API 응답 dict (postId, url 포함)
    """
    token = _get_token()

    data = {
        "access_token": token,
        "output": "json",
        "blogName": blog_name,
        "title": post.title,
        "content": post.html_content,
        "visibility": str(visibility),
        "category": "0",  # 기본 카테고리 (필요 시 카테고리 ID로 변경)
        "tag": ",".join(post.tags),
    }

    resp = httpx.post(f"{TISTORY_API}/post/write", data=data)
    resp.raise_for_status()
    result = resp.json()

    if result.get("tistory", {}).get("status") != "200":
        raise RuntimeError(f"티스토리 발행 실패: {result}")

    return result["tistory"]["postId"]


def get_blog_name(blog_type: str) -> str:
    """블로그 타입에 맞는 블로그 이름을 반환한다."""
    if blog_type == "dev":
        name = os.getenv("TISTORY_BLOG_DEV", "")
    else:
        name = os.getenv("TISTORY_BLOG_CPC", "")

    if not name:
        raise RuntimeError(
            f".env에 TISTORY_BLOG_{'DEV' if blog_type == 'dev' else 'CPC'}를 설정해주세요.\n"
            "  예: TISTORY_BLOG_DEV=myblog"
        )

    # xxx.tistory.com 형태면 xxx만 추출
    return name.replace(".tistory.com", "").strip()
