"""스톡 이미지/영상 자동 검색 모듈.

무료 소스:
1. Pixabay API (무료, 키 필요 — pixabay.com에서 발급)
2. Pexels API (무료, 키 필요)
3. Unsplash (무료, 키 없이 source.unsplash.com 사용)
"""

import os
from pathlib import Path

import httpx


def search_pixabay(query: str, media_type: str = "photo", per_page: int = 3) -> list[dict]:
    """Pixabay에서 이미지/영상 검색."""
    api_key = os.getenv("PIXABAY_API_KEY", "")
    if not api_key:
        return []

    endpoint = "https://pixabay.com/api/"
    if media_type == "video":
        endpoint = "https://pixabay.com/api/videos/"

    try:
        resp = httpx.get(endpoint, params={
            "key": api_key,
            "q": query,
            "per_page": per_page,
            "safesearch": "true",
            "orientation": "vertical",
        }, timeout=10)
        data = resp.json()

        results = []
        for hit in data.get("hits", []):
            if media_type == "video":
                url = hit.get("videos", {}).get("medium", {}).get("url", "")
            else:
                url = hit.get("largeImageURL", "") or hit.get("webformatURL", "")
            if url:
                results.append({"url": url, "source": "pixabay", "query": query})
        return results
    except Exception:
        return []


def search_pexels(query: str, per_page: int = 3) -> list[dict]:
    """Pexels에서 이미지 검색."""
    api_key = os.getenv("PEXELS_API_KEY", "")
    if not api_key:
        return []

    try:
        resp = httpx.get("https://api.pexels.com/v1/search", params={
            "query": query,
            "per_page": per_page,
            "orientation": "portrait",
        }, headers={"Authorization": api_key}, timeout=10)
        data = resp.json()

        return [
            {"url": p.get("src", {}).get("large2x", ""), "source": "pexels", "query": query}
            for p in data.get("photos", [])
            if p.get("src", {}).get("large2x")
        ]
    except Exception:
        return []


def get_unsplash_url(query: str, width: int = 1080, height: int = 1920) -> str:
    """Unsplash에서 이미지 URL 생성 (API키 불필요)."""
    return f"https://source.unsplash.com/{width}x{height}/?{query.replace(' ', ',')}"


def download_image(url: str, output_path: Path) -> bool:
    """URL에서 이미지 다운로드."""
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 1000:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


def fetch_scene_image(keywords: list[str], output_path: Path) -> bool:
    """키워드로 씬 이미지를 자동 검색 + 다운로드.

    Pixabay → Pexels → Unsplash 순으로 시도.
    """
    query = " ".join(keywords[:3])
    query_en = query  # 영어 키워드 사용 (프롬프트에서 영어로 생성하도록)

    # 1) Pixabay
    results = search_pixabay(query_en)
    if results:
        if download_image(results[0]["url"], output_path):
            return True

    # 2) Pexels
    results = search_pexels(query_en)
    if results:
        if download_image(results[0]["url"], output_path):
            return True

    # 3) Unsplash (항상 가능, 키 불필요)
    url = get_unsplash_url(query_en)
    if download_image(url, output_path):
        return True

    return False


def fetch_all_scene_images(scenes: list[dict], output_dir: Path) -> list[Path | None]:
    """콘티의 모든 씬 이미지를 자동 다운로드."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    for scene in scenes:
        num = scene.get("scene_number", 0)
        # image_keywords 필드 사용 (프롬프트에서 생성)
        keywords = scene.get("image_keywords", [])
        if not keywords:
            # fallback: emphasis_keywords 또는 subtitle_text에서 추출
            keywords = scene.get("emphasis_keywords", [])
            if not keywords:
                subtitle = scene.get("subtitle_text", "")
                keywords = [subtitle] if subtitle else ["korea"]

        output_path = output_dir / f"scene_{num:02d}.jpg"
        if fetch_scene_image(keywords, output_path):
            paths.append(output_path)
        else:
            paths.append(None)

    return paths
