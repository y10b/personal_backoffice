"""
릴스 콘티 자동 생성기 - 브랜딩 채널용

사용법:
  # 썰 텍스트로 바로 콘티 생성
  python main.py story "롯데리아 첫날 감자튀김 쏟은 썰" --type "알바 썰"

  # 인기 릴스 URL 분석 -> 내 썰로 콘티 생성
  python main.py url "https://www.instagram.com/reel/..." --story "내 썰 내용" --type "알바 썰"

  # 인기 릴스 URL 분석만 (콘티 없이)
  python main.py url "https://www.instagram.com/reel/..." --analyze-only

  # 구조화된 분석 (JSON 저장 가능)
  python main.py url "https://www.instagram.com/reel/..." --analyze-only --structured

  # 로컬 영상 파일로 분석
  python main.py url --local "downloads/영상.mp4" --story "내 썰" --type "알바 썰"

  # 여러 영상 배치 분석 + 패턴 추출
  python main.py batch "URL1" "URL2" "URL3"

  # 블로그 초안 생성 (구글 시트 저장)
  python main.py blog dev "FastAPI 배포"
  python main.py blog cpc "청년 도약계좌"

  # 매일 초안 자동 생성 (dev 1개 + cpc 1개)
  python main.py daily

  # 구글 시트 초기화
  python main.py init-sheets

  # 결과를 파일로 저장
  python main.py story "썰 내용" -o conti.txt
  python main.py batch "URL1" "URL2" -o patterns.json
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    # Windows 콘솔 UTF-8 출력 보장
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    parser = argparse.ArgumentParser(
        description="릴스 콘티 자동 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-o", "--output", help="결과를 파일로 저장")

    sub = parser.add_subparsers(dest="mode", required=True)

    # story 모드
    story_parser = sub.add_parser("story", help="썰 텍스트로 콘티 생성")
    story_parser.add_argument("text", nargs="?", help="썰 텍스트 (없으면 직접 입력)")
    story_parser.add_argument(
        "--type", default="알바 썰",
        help="콘텐츠 유형 (알바 썰 / 개발 자랑 / 학습 공유 / 과거 썰)",
    )

    # url 모드
    url_parser = sub.add_parser("url", help="릴스 URL 분석 후 콘티 생성")
    url_parser.add_argument("url", nargs="?", help="릴스 URL")
    url_parser.add_argument("--local", help="로컬 영상 파일 경로 (다운로드 대신)")
    url_parser.add_argument("--story", help="내 썰 텍스트 (없으면 분석만)")
    url_parser.add_argument("--analyze-only", action="store_true", help="분석만 하고 콘티 생성 안 함")
    url_parser.add_argument("--structured", action="store_true", help="구조화된 JSON 분석 (저장/비교 가능)")
    url_parser.add_argument(
        "--type", default="알바 썰",
        help="콘텐츠 유형 (알바 썰 / 개발 자랑 / 학습 공유 / 과거 썰)",
    )

    # batch 모드
    batch_parser = sub.add_parser("batch", help="여러 영상 배치 분석 + 패턴 추출")
    batch_parser.add_argument("urls", nargs="+", help="분석할 영상 URL들")

    # blog 모드
    blog_parser = sub.add_parser("blog", help="블로그 초안 생성 (개발/고단가CPC)")
    blog_parser.add_argument("blog_type", choices=["dev", "cpc"], help="dev=개발블로그, cpc=고단가블로그")
    blog_parser.add_argument("keyword", nargs="?", help="메인 키워드 (없으면 키워드 추천)")
    blog_parser.add_argument("--context", default="", help="추가 컨텍스트/방향성")
    blog_parser.add_argument("--cpc-category", default="청년 지원금", help="CPC 카테고리 (청년 지원금/프리랜서 세금/N잡 수익/대출/보험/청년 주거)")
    blog_parser.add_argument("--topic-hint", default="", help="키워드 추천 시 힌트")

    # daily 모드
    daily_parser = sub.add_parser("daily", help="오늘치 블로그 초안 자동 생성 (dev 1개 + cpc 1개)")
    daily_parser.add_argument("--dev-hint", default="", help="개발 블로그 키워드 힌트")
    daily_parser.add_argument("--cpc-hint", default="", help="CPC 블로그 키워드 힌트")

    # sheets 초기화
    sub.add_parser("init-sheets", help="구글 시트 초기화")

    args = parser.parse_args()

    # init-sheets는 API 키 불필요
    if args.mode == "init-sheets":
        load_dotenv(Path(__file__).parent / ".env")
        from sheets import init_sheets
        print("구글 시트 초기화 중...")
        init_sheets()
        return

    # argparse 이후에 API 키 체크 (--help가 먼저 동작하도록)
    load_dotenv(Path(__file__).parent / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "여기에_API키_입력":
        print("[오류] .env 파일에 GEMINI_API_KEY를 설정해주세요.")
        print("  https://aistudio.google.com/apikey 에서 무료 발급")
        sys.exit(1)

    from google import genai

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

    client = genai.Client(api_key=api_key)

    if args.mode == "story":
        text = args.text
        if not text:
            print("썰을 입력하세요 (입력 후 Ctrl+Z, Enter로 완료):")
            text = sys.stdin.read().strip()
        if not text:
            print("[오류] 썰 텍스트가 비어있습니다.")
            sys.exit(1)

        print(f"\n콘티 생성 중... (유형: {args.type})\n")
        conti = generate_from_story(text, args.type, client)
        output = format_conti(conti)

    elif args.mode == "url":
        # 영상 파일 준비
        if args.local:
            video_path = Path(args.local)
            if not video_path.exists():
                print(f"[오류] 파일을 찾을 수 없습니다: {args.local}")
                sys.exit(1)
        elif args.url:
            print("영상 다운로드 중...")
            video_path = download_reel(args.url)
            print(f"  저장: {video_path}")
        else:
            print("[오류] URL 또는 --local 경로를 지정해주세요.")
            sys.exit(1)

        if args.structured or args.analyze_only:
            # 구조화된 분석
            analysis = analyze_video_structured(
                video_path, client, url=args.url or ""
            )

            if args.analyze_only:
                output = format_analysis(analysis)
                # JSON 저장 시 raw 데이터도 함께
                if args.output and args.output.endswith(".json"):
                    Path(args.output).write_text(
                        json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    print(f"\nJSON 저장 완료: {args.output}")
                    print(output)
                    return
            else:
                # 구조화 분석 후 콘티 생성
                story = args.story
                if not story:
                    print("\n영상 분석 완료! 이제 내 썰을 입력하세요 (Ctrl+Z, Enter로 완료):")
                    story = sys.stdin.read().strip()
                if not story:
                    print("[오류] 썰 텍스트가 비어있습니다. --analyze-only 로 분석만 할 수 있습니다.")
                    sys.exit(1)

                print(f"\n참고 영상 기반 콘티 생성 중... (유형: {args.type})\n")
                conti = generate_from_reference(
                    format_analysis(analysis), story, args.type, client
                )
                output = format_conti(conti)
        else:
            # 기존 텍스트 분석
            analysis = analyze_video(video_path, client)

            if args.analyze_only:
                output = f"{'='*50}\n영상 분석 결과\n{'='*50}\n\n{analysis}"
            else:
                story = args.story
                if not story:
                    print("\n영상 분석 완료! 이제 내 썰을 입력하세요 (Ctrl+Z, Enter로 완료):")
                    story = sys.stdin.read().strip()
                if not story:
                    print("[오류] 썰 텍스트가 비어있습니다. --analyze-only 로 분석만 할 수 있습니다.")
                    sys.exit(1)

                print(f"\n참고 영상 기반 콘티 생성 중... (유형: {args.type})\n")
                conti = generate_from_reference(analysis, story, args.type, client)
                output = format_conti(conti)

    elif args.mode == "batch":
        print(f"\n{len(args.urls)}개 영상 배치 분석 시작\n")
        analyses = analyze_batch(args.urls, client)

        if not analyses:
            print("[오류] 분석 성공한 영상이 없습니다.")
            sys.exit(1)

        print(f"\n{len(analyses)}개 영상 분석 완료, 패턴 추출 중...\n")
        patterns = extract_patterns(analyses, client)
        output = format_patterns(patterns)

        # JSON 저장
        if args.output and args.output.endswith(".json"):
            data = {
                "analyses": [a.model_dump() for a in analyses],
                "patterns": patterns.model_dump(),
            }
            Path(args.output).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"JSON 저장 완료: {args.output}")
            print(output)
            return

    elif args.mode == "blog":
        from sheets import save_draft

        if not args.keyword:
            # 키워드 추천 모드
            label = "개발" if args.blog_type == "dev" else "CPC (청년/경제)"
            print(f"\n{label} 블로그 키워드 추천 중...\n")
            keywords = suggest_keywords(args.blog_type, args.topic_hint, client)
            print(f"{'='*50}")
            print(f"추천 키워드")
            print(f"{'='*50}")
            for i, kw in enumerate(keywords, 1):
                print(f"\n  [{i}] {kw.get('keyword', '')}")
                print(f"      검색의도: {kw.get('search_intent', '')}")
                print(f"      난이도: {kw.get('difficulty', '')}")
                print(f"      제목 예시: {kw.get('suggested_title', '')}")
            print(f"\n사용법: python main.py blog {args.blog_type} \"키워드\"")
            return

        # 초안 생성 -> 구글 시트 저장
        print(f"\n블로그 초안 생성 중... (키워드: {args.keyword})\n")
        if args.blog_type == "dev":
            post = generate_dev_post(args.keyword, args.context, client)
        else:
            post = generate_high_cpc_post(
                args.keyword, args.cpc_category, args.context, client
            )

        draft_id = save_draft(post, args.blog_type)
        output = format_blog_post(post)
        print(f"\n  초안 저장 완료! (ID: {draft_id})")
        print(f"  대시보드에서 리뷰 후 발행: http://127.0.0.1:8000/dashboard")

    elif args.mode == "daily":
        from sheets import save_draft

        print("\n오늘치 블로그 초안 자동 생성\n")

        # 1. 개발 블로그
        print("[1/2] 개발 블로그 초안 생성 중...")
        dev_keywords = suggest_keywords("dev", args.dev_hint, client)
        dev_kw = dev_keywords[0]["keyword"] if dev_keywords else "개발 팁"
        print(f"  키워드: {dev_kw}")
        dev_post = generate_dev_post(dev_kw, "", client)
        dev_id = save_draft(dev_post, "dev")
        print(f"  저장 완료! (ID: {dev_id}) - {dev_post.title}")

        # 2. CPC 블로그
        print("\n[2/2] CPC 블로그 초안 생성 중...")
        cpc_keywords = suggest_keywords("cpc", args.cpc_hint, client)
        cpc_kw = cpc_keywords[0]["keyword"] if cpc_keywords else "청년 지원금"
        print(f"  키워드: {cpc_kw}")
        cpc_post = generate_high_cpc_post(cpc_kw, "청년 지원금", "", client)
        cpc_id = save_draft(cpc_post, "cpc")
        print(f"  저장 완료! (ID: {cpc_id}) - {cpc_post.title}")

        output = (
            f"\n{'='*50}\n"
            f"오늘 초안 생성 완료!\n"
            f"{'='*50}\n"
            f"  개발: [{dev_id}] {dev_post.title}\n"
            f"  CPC:  [{cpc_id}] {cpc_post.title}\n\n"
            f"대시보드에서 리뷰 후 발행: http://127.0.0.1:8000/dashboard"
        )

    # 결과 출력
    print(output)

    # 파일 저장
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"\n저장 완료: {args.output}")


if __name__ == "__main__":
    main()
