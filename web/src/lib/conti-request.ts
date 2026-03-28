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

export async function createContiRequest(data: {
  type: "url" | "story";
  url?: string;
  story: string;
  contentType: string;
}) {
  const sheets = getSheets();
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const time = now.toTimeString().slice(0, 5);

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "릴스-요청!A:A",
  });
  const ids = (res.data.values || []).slice(1);
  const reqId = `REQ${String(ids.length + 1).padStart(4, "0")}`;

  await sheets.spreadsheets.values.append({
    spreadsheetId: SHEET_ID(),
    range: "릴스-요청!A:H",
    valueInputOption: "RAW",
    requestBody: {
      values: [[reqId, today, time, data.type, data.url || "", data.story, data.contentType, "대기"]],
    },
  });

  // Cloud Run 워커 트리거
  const workerUrl = process.env.REEL_WORKER_URL;
  if (workerUrl) {
    fetch(workerUrl, { method: "POST" }).catch(() => {});
  }

  return reqId;
}

export async function getContiRequests() {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "릴스-요청!A:H",
  });
  const [headers, ...rows] = res.data.values || [];
  if (!headers) return [];

  return rows.map((row) => {
    const obj: Record<string, string> = {};
    headers.forEach((h: string, i: number) => { obj[h] = row[i] || ""; });
    return obj;
  });
}
