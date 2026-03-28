import { GoogleGenAI } from "@google/genai";

function getClient() {
  return new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });
}

function cleanJson(text: string): string {
  const match = text.match(/```(?:json)?\s*\n?(.*?)\n?\s*```/s);
  return match ? match[1].trim() : text.trim();
}

export async function suggestKeywords(blogType: string, topicHint: string) {
  const ai = getClient();

  const typeDesc = blogType === "dev"
    ? "개발 블로그 (프로그래밍, 개발 도구, 창업, 프로젝트)"
    : "청년 N잡러·프리랜서 경제 정보 블로그 (청년 정책, 세금, 대출, 보험, 부업 수익)";

  const extra = blogType === "dev"
    ? "개발자/IT 종사자가 검색하는 키워드"
    : "광고 단가(CPC)가 높은 청년 지원금/프리랜서 세금/N잡 경제/대출·금융상품/보험/청년 주거 키워드";

  const prompt = `너는 SEO 키워드 리서치 전문가야.
## 블로그 유형
${typeDesc}
## 요청
${topicHint || "이번 주 트렌드에 맞는 키워드 추천"}
다음 조건에 맞는 블로그 키워드 5개를 추천해줘:
1. 검색량이 있을 것
2. 경쟁이 너무 치열하지 않을 것
3. 롱테일 키워드 포함 (3~5단어 조합)
4. ${extra}
각 키워드마다: keyword, search_intent, difficulty, suggested_title
JSON 배열로 출력해. 다른 텍스트 없이.`;

  const res = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: prompt,
    config: { responseMimeType: "application/json" },
  });

  return JSON.parse(cleanJson(res.text || "[]"));
}

export async function generateBlogPost(blogType: string, keyword: string, context: string, cpcCategory: string) {
  const ai = getClient();

  const prompt = blogType === "dev" ? getDevPrompt(keyword, context) : getCpcPrompt(keyword, cpcCategory, context);

  const res = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: prompt,
    config: { responseMimeType: "application/json" },
  });

  return JSON.parse(cleanJson(res.text || "{}"));
}

export async function generateThreads(title: string, htmlContent: string, count = 3) {
  const ai = getClient();

  const prompt = `다음 블로그 글을 Threads(쓰레드) 마케팅 글 ${count}개로 변환해줘.

## 블로그 제목
${title}

## 블로그 본문
${htmlContent.replace(/<[^>]*>/g, " ").slice(0, 2000)}

## 규칙
1. 각 글은 500자 이내
2. 핵심 정보 1개만 담기 (정보 과부하 X)
3. 톤: MZ세대 구어체, 공감 유발
4. 첫 줄이 훅 (스크롤 멈추게)
5. 마지막에 "자세한 내용은 블로그에" 같은 CTA
6. 해시태그 3~5개 포함
7. 글마다 다른 각도로 (같은 내용 반복 X)

JSON 배열로 출력해. 각 요소는 string (글 내용).
예: ["글1내용", "글2내용", "글3내용"]
JSON만 출력해.`;

  const res = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: prompt,
    config: { responseMimeType: "application/json" },
  });

  return JSON.parse(cleanJson(res.text || "[]"));
}

function getDevPrompt(keyword: string, context: string) {
  return `너는 개발 블로그 전문 작가야. SEO에 최적화된 기술 블로그 글을 작성해.
## 크리에이터 정보
- 상황: 개발자 + 창업 준비 중
- 톤: 친근하면서 전문적. "~해요/~거든요" 체
- 독자: 주니어~미드 개발자, 비전공자
## 주제/키워드
메인 키워드: ${keyword}
추가 컨텍스트: ${context}
## SEO 규칙
1. 제목: 메인 키워드 포함, 32자 내외
2. 메타 디스크립션: 155자 내외
3. H2 3~5개, 첫 문단에 키워드, 볼드/리스트 활용
4. 글 길이: 1500~2500자
5. 마지막에 CTA
## 출력 JSON
{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[{"position":"","alt_text":"","prompt":""}],"estimated_reading_min":5,"cpc_category":""}
HTML은 티스토리 호환. JSON만 출력해.`;
}

function getCpcPrompt(keyword: string, cpcCategory: string, context: string) {
  return `너는 청년 N잡러/프리랜서 대상 경제 정보 블로그 전문 작가야.
## 블로그 정체성
- 운영자: 알바+개발+창업 병행하는 N잡러
- 독자: 20~30대 청년, N잡러, 프리랜서
- 톤: 정보 전달이지만 공감 표현 섞기
## CPC 카테고리: ${cpcCategory}
## 주제/키워드
메인 키워드: ${keyword}
추가 컨텍스트: ${context}
## SEO 규칙
1. 제목: 메인 키워드 포함, 32자 내외, 정보성
2. 메타 디스크립션: 155자 내외
3. H2 4~6개, 비교표/리스트 활용, 구체적 숫자
4. 글 길이: 2000~3000자
5. 면책 조항 포함
## 출력 JSON
{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[{"position":"","alt_text":"","prompt":""}],"estimated_reading_min":7,"cpc_category":"${cpcCategory}"}
HTML은 티스토리 호환. JSON만 출력해.`;
}
