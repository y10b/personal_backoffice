import { google } from "googleapis";

function getAuth() {
  const creds = JSON.parse(process.env.GOOGLE_SHEETS_CREDENTIALS_JSON || "{}");
  return new google.auth.GoogleAuth({
    credentials: creds,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"],
  });
}

function getSheets() {
  return google.sheets({ version: "v4", auth: getAuth() });
}

const SHEET_ID = () => process.env.GOOGLE_SHEETS_ID!;

export async function getDrafts(status?: string, date?: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "블로그-초안!A:P",
  });

  const [headers, ...rows] = res.data.values || [];
  if (!headers) return [];

  let records = rows.map((row) => {
    const obj: Record<string, string> = {};
    headers.forEach((h: string, i: number) => { obj[h] = row[i] || ""; });
    return obj;
  });

  if (status) records = records.filter((r) => r["상태"] === status);
  if (date) records = records.filter((r) => r["날짜"] === date);

  return records;
}

export async function getDraftById(draftId: string) {
  const drafts = await getDrafts();
  return drafts.find((d) => d["ID"] === draftId) || null;
}

export async function updateDraftStatus(draftId: string, status: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "블로그-초안!A:A",
  });

  const ids = (res.data.values || []).map((r) => r[0]);
  const rowIdx = ids.indexOf(draftId);
  if (rowIdx < 0) throw new Error("초안을 찾을 수 없습니다.");

  await sheets.spreadsheets.values.update({
    spreadsheetId: SHEET_ID(),
    range: `블로그-초안!M${rowIdx + 1}`,
    valueInputOption: "RAW",
    requestBody: { values: [[status]] },
  });
}

export async function saveDraft(post: {
  title: string;
  meta_description: string;
  keywords: string[];
  slug: string;
  category: string;
  tags: string[];
  html_content: string;
  images: { position: string; alt_text: string; prompt: string }[];
  estimated_reading_min: number;
  cpc_category: string;
}, blogType: string) {
  const sheets = getSheets();
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const time = now.toTimeString().slice(0, 5);

  // Get next ID
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "블로그-초안!A:A",
  });
  const ids = (res.data.values || []).slice(1).map((r) => r[0]);
  const todayPrefix = today.replace(/-/g, "");
  const todayIds = ids.filter((id: string) => id?.startsWith(todayPrefix));
  const seq = todayIds.length + 1;
  const draftId = `${todayPrefix}-${String(seq).padStart(3, "0")}`;

  const row = [
    draftId, today, time, blogType, post.cpc_category,
    post.title, post.keywords.join(", "), post.slug, post.category,
    post.tags.join(", "), post.meta_description,
    String(post.estimated_reading_min), "초안",
    post.html_content,
    JSON.stringify(post.images),
    "",
  ];

  await sheets.spreadsheets.values.append({
    spreadsheetId: SHEET_ID(),
    range: "블로그-초안!A:P",
    valueInputOption: "RAW",
    requestBody: { values: [row] },
  });

  return draftId;
}

export async function recordPublish(draftId: string, blogType: string, blogName: string, title: string, keywords: string, postId: string) {
  const sheets = getSheets();
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "블로그-발행!A:A",
  });
  const ids = (res.data.values || []).slice(1);
  const publishId = `P${String(ids.length + 1).padStart(3, "0")}`;

  await sheets.spreadsheets.values.append({
    spreadsheetId: SHEET_ID(),
    range: "블로그-발행!A:I",
    valueInputOption: "RAW",
    requestBody: { values: [[publishId, draftId, now, blogType, blogName, title, keywords, postId, ""]] },
  });

  await updateDraftStatus(draftId, "발행완료");
  return publishId;
}

export async function getDashboardStats() {
  const sheets = getSheets();

  const [draftRes, pubRes] = await Promise.all([
    sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "블로그-초안!A:M" }),
    sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "블로그-발행!A:I" }),
  ]);

  const draftRows = (draftRes.data.values || []).slice(1);
  const pubRows = (pubRes.data.values || []).slice(1);
  const today = new Date().toISOString().slice(0, 10);

  const todayDrafts = draftRows.filter((r) => r[1] === today).length;
  // 초안 시트에서 오늘 날짜 + 발행완료 상태인 것을 카운트 (수동 발행 포함)
  const todayPublished = draftRows.filter((r) => r[1] === today && r[12] === "발행완료").length;

  const statusCounts: Record<string, number> = {};
  const typeCounts: Record<string, number> = { dev: 0, cpc: 0 };
  for (const r of draftRows) {
    statusCounts[r[12] || "알수없음"] = (statusCounts[r[12] || "알수없음"] || 0) + 1;
    if (r[3] === "dev") typeCounts.dev++;
    if (r[3] === "cpc") typeCounts.cpc++;
  }

  return {
    today,
    total_drafts: draftRows.length,
    total_published: draftRows.filter((r) => r[12] === "발행완료").length,
    today_drafts: todayDrafts,
    today_published: todayPublished,
    status_counts: statusCounts,
    type_counts: typeCounts,
  };
}
