// 블로그 표지 HTML 생성

export function generateDevCover(title: string, keywords: string[], date: string): string {
  const keyword = keywords[0] || "";
  const subKeywords = keywords.slice(1, 4).join(" · ");

  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { width: 800px; height: 420px; font-family: 'Noto Sans KR', sans-serif; overflow: hidden; }
  .card {
    width: 800px; height: 420px; padding: 48px 56px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    display: flex; flex-direction: column; justify-content: space-between;
    position: relative;
  }
  .card::before {
    content: ''; position: absolute; top: 0; right: 0; width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
  }
  .card::after {
    content: ''; position: absolute; bottom: 0; left: 0; width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%);
  }
  .top { display: flex; justify-content: space-between; align-items: flex-start; position: relative; z-index: 1; }
  .badge { background: rgba(99,102,241,0.2); color: #818cf8; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 700; letter-spacing: 1px; }
  .date { color: #64748b; font-size: 14px; font-weight: 400; }
  .middle { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; justify-content: center; }
  .title { color: #f1f5f9; font-size: 32px; font-weight: 900; line-height: 1.4; margin-bottom: 12px; word-break: keep-all; }
  .keyword { color: #10b981; font-size: 15px; font-weight: 700; margin-bottom: 6px; }
  .sub-keywords { color: #64748b; font-size: 13px; }
  .bottom { display: flex; justify-content: space-between; align-items: flex-end; position: relative; z-index: 1; }
  .blog-name { color: #475569; font-size: 13px; font-weight: 700; letter-spacing: 2px; }
  .terminal { color: #10b981; font-size: 16px; font-family: 'Courier New', monospace; opacity: 0.6; }
</style></head>
<body>
<div class="card">
  <div class="top">
    <span class="badge">DEV</span>
    <span class="date">${date}</span>
  </div>
  <div class="middle">
    <div class="keyword">${keyword}</div>
    <div class="title">${title}</div>
    <div class="sub-keywords">${subKeywords}</div>
  </div>
  <div class="bottom">
    <span class="blog-name">개발막차</span>
    <span class="terminal">&gt;_</span>
  </div>
</div>
</body></html>`;
}

export function generateCpcCover(title: string, keywords: string[], date: string, cpcCategory: string): string {
  const mainStat = extractStat(title);

  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { width: 800px; height: 420px; font-family: 'Noto Sans KR', sans-serif; overflow: hidden; }
  .card {
    width: 800px; height: 420px; padding: 48px 56px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
    display: flex; flex-direction: column; justify-content: space-between;
    position: relative;
  }
  .card::before {
    content: ''; position: absolute; top: -50px; right: -50px; width: 350px; height: 350px;
    background: radial-gradient(circle, rgba(245,158,11,0.12) 0%, transparent 70%);
  }
  .top { display: flex; justify-content: space-between; align-items: flex-start; position: relative; z-index: 1; }
  .category { background: rgba(245,158,11,0.2); color: #fbbf24; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 700; }
  .date { color: #64748b; font-size: 14px; }
  .middle { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; justify-content: center; }
  .stat-row { display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
  .stat-num { color: #fbbf24; font-size: 42px; font-weight: 900; }
  .stat-label { color: #94a3b8; font-size: 15px; }
  .title { color: #f1f5f9; font-size: 28px; font-weight: 900; line-height: 1.4; word-break: keep-all; }
  .sub { color: #64748b; font-size: 13px; margin-top: 10px; }
  .bottom { display: flex; justify-content: space-between; align-items: flex-end; position: relative; z-index: 1; }
  .blog-name { color: #475569; font-size: 13px; font-weight: 700; letter-spacing: 2px; }
  .year { color: #fbbf24; font-size: 14px; font-weight: 700; opacity: 0.5; }
</style></head>
<body>
<div class="card">
  <div class="top">
    <span class="category">${cpcCategory}</span>
    <span class="date">${date}</span>
  </div>
  <div class="middle">
    ${mainStat.num ? `<div class="stat-row"><span class="stat-num">${mainStat.num}</span><span class="stat-label">${mainStat.label}</span></div>` : ""}
    <div class="title">${title}</div>
    <div class="sub">${keywords.slice(0, 4).join(" · ")}</div>
  </div>
  <div class="bottom">
    <span class="blog-name">N잡러 경제노트</span>
    <span class="year">2026</span>
  </div>
</div>
</body></html>`;
}

function extractStat(title: string): { num: string; label: string } {
  // 제목에서 숫자 추출 (예: "2026 청년 도약계좌 월 70만원" → "70만원")
  const match = title.match(/(\d[\d,.]*\s*(?:만원|만|%|억|천만|개|가지|단계|조건))/);
  if (match) {
    const full = match[1];
    const numMatch = full.match(/(\d[\d,.]*)/);
    const unitMatch = full.match(/(만원|만|%|억|천만|개|가지|단계|조건)/);
    return { num: (numMatch?.[1] || "") + (unitMatch?.[1] || ""), label: "" };
  }

  // 연도 추출
  const yearMatch = title.match(/(2026|2025)/);
  if (yearMatch) return { num: yearMatch[1], label: "년 기준" };

  return { num: "", label: "" };
}
