"""뉴스 소스 모듈 — 국뽕+경제 숏폼용 트렌딩 토픽 수집.

소스:
1. Reddit (r/korea, r/nottheonion, r/worldnews) — 무료
2. NewsAPI.org — 무료 100요청/일
3. Currents API — 무료 600요청/일
"""

import os
import httpx


def fetch_reddit_posts(subreddit: str, sort: str = "hot", limit: int = 10) -> list[dict]:
    """Reddit에서 인기 게시물 가져오기."""
    headers = {"User-Agent": "reel-maker/1.0"}
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"

    try:
        resp = httpx.get(url, headers=headers, timeout=10)
        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            if d.get("stickied"):
                continue
            posts.append({
                "title": d.get("title", ""),
                "url": d.get("url", ""),
                "score": d.get("score", 0),
                "subreddit": subreddit,
                "source": "reddit",
            })
        return posts
    except Exception:
        return []


def fetch_newsapi(query: str, language: str = "ko", page_size: int = 10) -> list[dict]:
    """NewsAPI.org에서 뉴스 검색."""
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        return []

    try:
        resp = httpx.get("https://newsapi.org/v2/everything", params={
            "q": query,
            "language": language,
            "sortBy": "popularity",
            "pageSize": page_size,
            "apiKey": api_key,
        }, timeout=10)
        data = resp.json()
        return [
            {
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "url": a.get("url", ""),
                "source": a.get("source", {}).get("name", ""),
            }
            for a in data.get("articles", [])
        ]
    except Exception:
        return []


def fetch_currents(query: str, language: str = "ko") -> list[dict]:
    """Currents API에서 뉴스 검색."""
    api_key = os.getenv("CURRENTS_API_KEY", "")
    if not api_key:
        return []

    try:
        resp = httpx.get("https://api.currentsapi.services/v1/search", params={
            "keywords": query,
            "language": language,
            "apiKey": api_key,
        }, timeout=10)
        data = resp.json()
        return [
            {
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "url": a.get("url", ""),
                "source": a.get("author", ""),
            }
            for a in data.get("news", [])
        ]
    except Exception:
        return []


def get_trending_topics() -> list[dict]:
    """국뽕+경제 숏폼용 트렌딩 토픽 수집."""
    all_topics = []

    # Reddit — 한국 관련 해외 반응
    all_topics.extend(fetch_reddit_posts("korea", "hot", 10))
    all_topics.extend(fetch_reddit_posts("kpop", "hot", 5))

    # NewsAPI — 한국 경제/기술 뉴스
    for query in ["한국 세계 최초", "한국 경제", "K-pop 해외", "삼성 반도체", "한국 기술"]:
        all_topics.extend(fetch_newsapi(query, "ko", 5))

    # Currents — 보조
    for query in ["Korea technology", "Korea economy", "K-culture"]:
        all_topics.extend(fetch_currents(query, "en"))

    # 중복 제거 (제목 기준)
    seen = set()
    unique = []
    for t in all_topics:
        title = t["title"].strip()
        if title and title not in seen:
            seen.add(title)
            unique.append(t)

    return unique[:20]  # 상위 20개
