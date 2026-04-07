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
  return `너는 10년차 시니어 개발자이자 SEO 전문가야. 티스토리 개발 블로그 "개발막차"의 글을 작성해.

## 필수 규칙
- 2026년 기준. 실제 존재하는 정확한 정보만. 거짓/추측 절대 금지.
- 버전, 명령어, API는 실제 것만. 불확실하면 아예 안 쓰거나 "공식 문서 확인" 안내.
- "(확인 필요)" 같은 메타 표시 본문에 절대 포함하지 마.

## SEO 규칙 (엄격)
1. 제목: 메인 키워드가 앞쪽에 위치. 32자 내외. "2026" 포함.
   좋은 예: "Next.js 15 서버 컴포넌트 완벽 가이드 (2026)"
   나쁜 예: "주니어 개발자를 위한 완벽 가이드"
2. H2: 모든 H2에 키워드 변형 포함. 인사말/감성 H2 금지.
   좋은 예: "<h2>Next.js 15 서버 컴포넌트란?</h2>"
   나쁜 예: "<h2>안녕하세요!</h2>", "<h2>마무리하며</h2>"
3. 첫 문장: 메인 키워드로 시작. 인사말 없이 바로 본론.
   좋은 예: "Next.js 15의 서버 컴포넌트는 렌더링 성능을..."
   나쁜 예: "안녕하세요! 오늘은 ~에 대해 알아볼게요."
4. 메타 디스크립션: 155자. 키워드 + 핵심 가치 + 행동 유도.
5. 본문: H2 4~5개, H3 활용, 코드블록 필수, 비교표, 주의사항 박스.
6. 내부 밀도: 서론 3줄 이내로 끝내고 바로 본론. 쓸데없는 감탄 금지.
7. 글 길이: 2000~3000자 (HTML 기준).

## 톤
- "~거든요", "~인데요" 체. 친근하지만 정보 밀도 높게.
- 뻔한 설명 생략. 핵심만. 코드 먼저, 설명은 뒤에.
- 실무에서 실제로 겪는 문제 중심으로.

## 키워드: ${keyword}
## 컨텍스트: ${context}

## JSON
{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[{"position":"","alt_text":"","prompt":""}],"estimated_reading_min":5,"cpc_category":""}
HTML은 티스토리에 바로 붙여넣기 가능한 깔끔한 HTML. JSON만 출력.`;
}

function getCpcPrompt(keyword: string, cpcCategory: string, context: string) {
  return `너는 청년 경제/재테크 전문 블로거야. 티스토리 CPC 블로그의 글을 작성해.

## 필수 규칙
- 2026년 기준. 실제 존재하는 정확한 정보만.
- 지원금 금액, 자격 조건, 신청 기간, 금리는 실제 2026년 데이터.
- 없는 제도 지어내지 마. 확실한 것만.
- "(확인 필요)" 같은 메타 표시 본문에 포함하지 마. 대신 "정확한 조건은 [기관명] 홈페이지에서 확인하세요"로 자연스럽게 안내.

## SEO 규칙 (엄격)
1. 제목: 메인 키워드가 앞쪽. 32자 내외. "2026" 포함. 숫자 활용.
   좋은 예: "2026 청년 도약계좌 조건·금리·신청방법 총정리"
   나쁜 예: "N잡러를 위한 완벽 가이드!"
2. H2: 모든 H2에 키워드 변형. 검색 의도 반영.
   좋은 예: "<h2>청년 도약계좌 가입 조건 (2026년)</h2>"
   나쁜 예: "<h2>왜 지금 시작해야 할까요?</h2>"
3. 첫 문장: 메인 키워드 포함. 인사말 없이 핵심 정보부터.
   좋은 예: "2026년 청년 도약계좌는 월 최대 70만원을 납입하면..."
   나쁜 예: "안녕하세요! 오늘은 청년을 위한..."
4. 메타 디스크립션: 155자. 키워드 + 핵심 수치 + 행동 유도.
5. 본문: H2 4~6개, 비교표(<table>) 필수 1개 이상, 리스트 활용, 신청 방법 단계별.
6. 서론 3줄 이내. 바로 본론. 감성 서론 금지.
7. 글 길이: 2500~3500자.
8. 면책 조항: 글 맨 마지막에 "<p><em>이 글은 2026년 기준 정보입니다. 정확한 조건은 관련 기관 홈페이지에서 확인하시기 바랍니다.</em></p>"

## 톤
- "~입니다" 기본 + 중간중간 "~거든요" 섞어서 딱딱하지 않게.
- 숫자와 데이터 중심. 감성 표현 최소화.
- "실제로 제가 알아본 결과" 같은 경험 기반 표현 자연스럽게.

## CPC 카테고리: ${cpcCategory}
## 키워드: ${keyword}
## 컨텍스트: ${context}

## JSON
{"title":"","meta_description":"","keywords":[],"slug":"","category":"","tags":[],"html_content":"","images":[{"position":"","alt_text":"","prompt":""}],"estimated_reading_min":7,"cpc_category":"${cpcCategory}"}
HTML은 티스토리 호환. JSON만 출력.`;
}
