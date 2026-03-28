"""릴스 콘티 생성기 - 웹 서버"""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from google import genai
from pydantic import BaseModel

from analyzer import (
    analyze_batch,
    analyze_video,
    analyze_video_structured,
    download_reel,
    extract_patterns,
    format_analysis,
    format_patterns,
)
from blog_generator import (
    format_blog_post,
    generate_dev_post,
    generate_high_cpc_post,
    suggest_keywords,
)
from generator import format_conti, generate_from_reference, generate_from_story
from scene_image import generate_scene_image
from trading import get_trading_dashboard
from sheets import (
    get_dashboard_stats,
    get_draft_by_id,
    get_drafts,
    init_sheets,
    record_publish,
    save_draft,
    update_draft_content,
    update_draft_status,
)
from tistory import exchange_token, get_auth_url, get_blog_name, post_to_tistory

load_dotenv(Path(__file__).parent / ".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(".env에 GEMINI_API_KEY를 설정해주세요.")

client = genai.Client(api_key=api_key)
app = FastAPI(title="릴스 콘티 생성기")


class StoryRequest(BaseModel):
    story: str
    content_type: str = "알바 썰"


class UrlRequest(BaseModel):
    url: str
    story: str | None = None
    content_type: str = "알바 썰"
    analyze_only: bool = False


class BatchAnalyzeRequest(BaseModel):
    urls: list[str]


class BlogKeywordRequest(BaseModel):
    blog_type: str = "dev"  # "dev" or "cpc"
    topic_hint: str = ""


class BlogGenerateRequest(BaseModel):
    blog_type: str = "dev"
    keyword: str
    context: str = ""
    cpc_category: str = "청년 지원금"


class DraftUpdateRequest(BaseModel):
    html_content: str | None = None
    status: str | None = None
    memo: str = ""


class PublishRequest(BaseModel):
    draft_id: str
    visibility: int = 0  # 기본 비공개 (안전)


class SceneImageRequest(BaseModel):
    subtitle_text: str
    emphasis_keywords: list[str] = []
    visual_description: str = ""
    capcut_notes: str = ""
    scene_number: int = 1


class ContiResponse(BaseModel):
    success: bool
    result: str
    raw: dict | None = None


def _attach_images(raw: dict) -> dict:
    """text_overlay 씬에 base64 이미지를 첨부한다."""
    if not raw or "scenes" not in raw:
        return raw
    for scene in raw["scenes"]:
        if scene.get("scene_type") == "text_overlay":
            try:
                img_bytes = generate_scene_image(
                    subtitle_text=scene.get("subtitle_text", ""),
                    emphasis_keywords=scene.get("emphasis_keywords", []),
                    visual_description=scene.get("visual_description", ""),
                    capcut_notes=scene.get("capcut_notes", ""),
                    scene_number=scene.get("scene_number", 1),
                )
                scene["image_base64"] = base64.b64encode(img_bytes).decode()
            except Exception:
                scene["image_base64"] = None
        else:
            scene["image_base64"] = None
    return raw


@app.post("/api/story", response_model=ContiResponse)
def create_from_story(req: StoryRequest):
    try:
        conti = generate_from_story(req.story, req.content_type, client)
        raw = conti.model_dump()
        raw = _attach_images(raw)
        return ContiResponse(
            success=True,
            result=format_conti(conti),
            raw=raw,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/url", response_model=ContiResponse)
def create_from_url(req: UrlRequest):
    try:
        video_path = download_reel(req.url)
        analysis = analyze_video(video_path, client)

        if req.analyze_only or not req.story:
            return ContiResponse(success=True, result=analysis)

        conti = generate_from_reference(
            analysis, req.story, req.content_type, client
        )
        raw = conti.model_dump()
        raw = _attach_images(raw)
        return ContiResponse(
            success=True,
            result=format_conti(conti),
            raw=raw,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
def analyze_structured(req: UrlRequest):
    """영상을 구조화된 JSON으로 분석한다."""
    try:
        video_path = download_reel(req.url)
        analysis = analyze_video_structured(video_path, client, url=req.url)
        return {
            "success": True,
            "result": format_analysis(analysis),
            "raw": analysis.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch-analyze")
def batch_analyze(req: BatchAnalyzeRequest):
    """여러 영상을 배치 분석하고 공통 패턴을 추출한다."""
    try:
        analyses = analyze_batch(req.urls, client)
        if not analyses:
            raise HTTPException(status_code=400, detail="분석 성공한 영상이 없습니다.")

        patterns = extract_patterns(analyses, client)
        return {
            "success": True,
            "analyses": [a.model_dump() for a in analyses],
            "patterns": patterns.model_dump(),
            "formatted_patterns": format_patterns(patterns),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scene-image")
def create_scene_image(req: SceneImageRequest):
    """개별 씬 이미지를 PNG로 반환한다."""
    try:
        img_bytes = generate_scene_image(
            subtitle_text=req.subtitle_text,
            emphasis_keywords=req.emphasis_keywords,
            visual_description=req.visual_description,
            capcut_notes=req.capcut_notes,
            scene_number=req.scene_number,
        )
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 블로그 API ──


@app.post("/api/blog/keywords")
def blog_keywords(req: BlogKeywordRequest):
    """키워드 추천."""
    try:
        keywords = suggest_keywords(req.blog_type, req.topic_hint, client)
        return {"success": True, "keywords": keywords}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/blog/generate")
def blog_generate(req: BlogGenerateRequest):
    """블로그 초안 생성 → 구글 시트 저장."""
    try:
        if req.blog_type == "dev":
            post = generate_dev_post(req.keyword, req.context, client)
        else:
            post = generate_high_cpc_post(
                req.keyword, req.cpc_category, req.context, client
            )

        draft_id = save_draft(post, req.blog_type)

        return {
            "success": True,
            "draft_id": draft_id,
            "formatted": format_blog_post(post),
            "raw": post.model_dump(),
            "message": f"초안 저장 완료 ({draft_id}). 대시보드에서 리뷰 후 발행하세요.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 대시보드 / 초안 관리 API ──


@app.get("/api/dashboard")
def dashboard():
    """대시보드 통계."""
    try:
        return {"success": True, **get_dashboard_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/drafts")
def list_drafts(status: str | None = None, date: str | None = None):
    """초안 목록 조회."""
    try:
        drafts = get_drafts(status=status, date=date)
        return {"success": True, "drafts": drafts, "count": len(drafts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/drafts/{draft_id}")
def get_draft(draft_id: str):
    """초안 상세 조회."""
    try:
        draft = get_draft_by_id(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="초안을 찾을 수 없습니다.")
        return {"success": True, "draft": draft}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/drafts/{draft_id}")
def update_draft(draft_id: str, req: DraftUpdateRequest):
    """초안 수정 (본문/상태)."""
    try:
        if req.html_content:
            update_draft_content(draft_id, req.html_content)
        if req.status:
            update_draft_status(draft_id, req.status, req.memo)
        return {"success": True, "message": f"초안 {draft_id} 업데이트 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/publish")
def publish_draft(req: PublishRequest):
    """초안을 티스토리에 발행."""
    try:
        draft = get_draft_by_id(req.draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="초안을 찾을 수 없습니다.")

        if draft.get("상태") not in ("초안", "수정완료"):
            raise HTTPException(
                status_code=400,
                detail=f"발행할 수 없는 상태입니다: {draft.get('상태')}"
            )

        blog_type = draft.get("블로그타입", "dev")
        blog_name = get_blog_name(blog_type)

        from models import BlogPost
        post = BlogPost(
            title=draft["제목"],
            meta_description=draft.get("메타디스크립션", ""),
            keywords=[k.strip() for k in draft.get("키워드", "").split(",")],
            slug=draft.get("슬러그", ""),
            category=draft.get("카테고리", ""),
            tags=[t.strip() for t in draft.get("태그", "").split(",")],
            html_content=draft.get("HTML본문", ""),
            images=[],
            estimated_reading_min=int(draft.get("읽기시간(분)", 5)),
            cpc_category=draft.get("CPC카테고리", ""),
        )

        post_id = post_to_tistory(post, blog_name, visibility=req.visibility)

        record_publish(
            draft_id=req.draft_id,
            blog_type=blog_type,
            blog_name=blog_name,
            title=post.title,
            keywords=draft.get("키워드", ""),
            post_id=str(post_id),
        )

        return {
            "success": True,
            "post_id": post_id,
            "message": f"발행 완료! (postId: {post_id})",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sheets/init")
def sheets_init():
    """구글 시트 초기화."""
    try:
        init_sheets()
        return {"success": True, "message": "구글 시트 초기화 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/tistory")
def tistory_auth():
    """티스토리 OAuth 인증 URL 리다이렉트."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(get_auth_url())


@app.get("/callback/tistory")
def tistory_callback(code: str):
    """티스토리 OAuth 콜백 → 토큰 발급."""
    try:
        token = exchange_token(code)
        return HTMLResponse(
            f"<h2>인증 완료!</h2>"
            f"<p>.env에 추가하세요:</p>"
            f"<code>TISTORY_ACCESS_TOKEN={token}</code>"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trading")
def trading_dashboard():
    """자동매매 대시보드 데이터."""
    try:
        return {"success": True, **get_trading_dashboard()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    html_path = Path(__file__).parent / "static" / "dashboard.html"
    return html_path.read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
