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

// ── 릴스 콘티 ──

export async function getContis(status?: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "릴스-콘티!A:J",
  });
  const [headers, ...rows] = res.data.values || [];
  if (!headers) return [];

  let records = rows.map((row) => {
    const obj: Record<string, string> = {};
    headers.forEach((h: string, i: number) => { obj[h] = row[i] || ""; });
    return obj;
  });

  if (status) records = records.filter((r) => r["상태"] === status);
  return records;
}

export async function saveConti(conti: {
  title: string;
  contentType: string;
  totalDuration: number;
  url?: string;
  contiJson: string;
  memo?: string;
}) {
  const sheets = getSheets();
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const time = now.toTimeString().slice(0, 5);

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "릴스-콘티!A:A",
  });
  const ids = (res.data.values || []).slice(1).map((r) => r[0]);
  const prefix = "R" + today.replace(/-/g, "");
  const seq = ids.filter((id: string) => id?.startsWith(prefix)).length + 1;
  const contiId = `${prefix}-${String(seq).padStart(3, "0")}`;

  await sheets.spreadsheets.values.append({
    spreadsheetId: SHEET_ID(),
    range: "릴스-콘티!A:J",
    valueInputOption: "RAW",
    requestBody: {
      values: [[
        contiId, today, time, conti.title, conti.contentType,
        conti.totalDuration, "초안", conti.url || "",
        conti.contiJson, conti.memo || "",
      ]],
    },
  });

  return contiId;
}

export async function updateContiStatus(contiId: string, status: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "릴스-콘티!A:A",
  });
  const ids = (res.data.values || []).map((r) => r[0]);
  const rowIdx = ids.indexOf(contiId);
  if (rowIdx < 0) throw new Error("콘티를 찾을 수 없습니다.");

  await sheets.spreadsheets.values.update({
    spreadsheetId: SHEET_ID(),
    range: `릴스-콘티!G${rowIdx + 1}`,
    valueInputOption: "RAW",
    requestBody: { values: [[status]] },
  });
}

// ── 쓰레드 ──

export async function getThreads(status?: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "쓰레드!A:F",
  });
  const [headers, ...rows] = res.data.values || [];
  if (!headers) return [];

  let records = rows.map((row) => {
    const obj: Record<string, string> = {};
    headers.forEach((h: string, i: number) => { obj[h] = row[i] || ""; });
    return obj;
  });

  if (status) records = records.filter((r) => r["상태"] === status);
  return records;
}

export async function saveThreads(threads: {
  sourceType: string;
  sourceId: string;
  contents: string[];
}) {
  const sheets = getSheets();
  const today = new Date().toISOString().slice(0, 10);

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "쓰레드!A:A",
  });
  const existingIds = (res.data.values || []).slice(1).length;

  const rows = threads.contents.map((content, i) => {
    const id = `T${String(existingIds + i + 1).padStart(4, "0")}`;
    return [id, today, threads.sourceType, threads.sourceId, content, "초안"];
  });

  await sheets.spreadsheets.values.append({
    spreadsheetId: SHEET_ID(),
    range: "쓰레드!A:F",
    valueInputOption: "RAW",
    requestBody: { values: rows },
  });

  return rows.map((r) => r[0]);
}

export async function updateThreadStatus(threadId: string, status: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "쓰레드!A:A",
  });
  const ids = (res.data.values || []).map((r) => r[0]);
  const rowIdx = ids.indexOf(threadId);
  if (rowIdx < 0) throw new Error("쓰레드를 찾을 수 없습니다.");

  await sheets.spreadsheets.values.update({
    spreadsheetId: SHEET_ID(),
    range: `쓰레드!F${rowIdx + 1}`,
    valueInputOption: "RAW",
    requestBody: { values: [[status]] },
  });
}

// ── 콘텐츠 캘린더 ──

export async function getCalendarData(month: string) {
  const sheets = getSheets();

  const [draftsRes, contisRes, threadsRes] = await Promise.all([
    sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "블로그-초안!A:M" }),
    sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "릴스-콘티!A:G" }),
    sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "쓰레드!A:F" }),
  ]);

  const blogDrafts = (draftsRes.data.values || []).slice(1)
    .filter((r) => (r[1] || "").startsWith(month))
    .map((r) => ({ date: r[1], type: "blog" as const, title: r[5], status: r[12], blogType: r[3], id: r[0] }));

  const contis = (contisRes.data.values || []).slice(1)
    .filter((r) => (r[1] || "").startsWith(month))
    .map((r) => ({ date: r[1], type: "reels" as const, title: r[3], status: r[6], id: r[0] }));

  const threads = (threadsRes.data.values || []).slice(1)
    .filter((r) => (r[1] || "").startsWith(month))
    .map((r) => ({ date: r[1], type: "threads" as const, title: (r[4] || "").slice(0, 30) + "...", status: r[5], id: r[0] }));

  return [...blogDrafts, ...contis, ...threads];
}

// ── 키워드 트래킹 ──

export async function getKeywordHistory(keyword?: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "키워드-트래킹!A:F",
  });
  let rows = (res.data.values || []).slice(1).map((r) => ({
    date: r[0] || "",
    keyword: r[1] || "",
    blogType: r[2] || "",
    postId: r[3] || "",
    googleRank: parseInt(r[4] || "0"),
    naverRank: parseInt(r[5] || "0"),
  }));

  if (keyword) rows = rows.filter((r) => r.keyword === keyword);
  return rows;
}

export async function saveKeywordRank(date: string, keyword: string, blogType: string, postId: string, googleRank: number, naverRank: number) {
  const sheets = getSheets();
  await sheets.spreadsheets.values.append({
    spreadsheetId: SHEET_ID(),
    range: "키워드-트래킹!A:F",
    valueInputOption: "RAW",
    requestBody: { values: [[date, keyword, blogType, postId, googleRank, naverRank]] },
  });
}
