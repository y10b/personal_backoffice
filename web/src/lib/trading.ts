import { google } from "googleapis";

function getAuth() {
  const creds = JSON.parse(process.env.GOOGLE_SHEETS_CREDENTIALS_JSON || "{}");
  return new google.auth.GoogleAuth({
    credentials: creds,
    scopes: ["https://www.googleapis.com/auth/spreadsheets.readonly"],
  });
}

function getSheets() {
  return google.sheets({ version: "v4", auth: getAuth() });
}

const SHEET_ID = () => process.env.GOOGLE_SHEETS_ID!;

export async function getTradingDashboard() {
  const sheets = getSheets();

  let balanceRes, holdingsRes, historyRes;
  try {
    [balanceRes, holdingsRes, historyRes] = await Promise.all([
      sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "매매-잔고!A:G" }),
      sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "매매-보유종목!A:K" }),
      sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID(), range: "매매-이력!A:E" }),
    ]);
  } catch (e) {
    console.error("Trading sheets read error:", e);
    return { balance: { holdings: [], total_eval: 0, total_pnl: 0, total_buy: 0, cash: 0 }, history: [], today_pnl: 0, week_pnl: 0, total_realized: 0, unrealized_pnl: 0 };
  }

  // 잔고 — 마지막 행 (최신)
  const balanceRows = (balanceRes.data.values || []).slice(1);
  const latestBalance = balanceRows[balanceRows.length - 1] || [];
  const balance = {
    date: latestBalance[0] || "",
    total_eval: parseInt(latestBalance[2] || "0"),
    total_buy: parseInt(latestBalance[3] || "0"),
    total_pnl: parseInt(latestBalance[4] || "0"),
    cash: parseInt(latestBalance[5] || "0"),
    holding_count: parseInt(latestBalance[6] || "0"),
  };

  // 보유종목 — 최신 날짜만
  const holdingRows = (holdingsRes.data.values || []).slice(1);
  const latestDate = holdingRows[holdingRows.length - 1]?.[0] || "";
  const holdings = holdingRows
    .filter((r) => r[0] === latestDate)
    .map((r) => ({
      code: r[1] || "",
      name: r[2] || "",
      qty: parseInt(r[3] || "0"),
      buy_price: parseInt(r[4] || "0"),
      cur_price: parseInt(r[5] || "0"),
      pnl_pct: parseFloat(r[6] || "0"),
      pnl: parseInt(r[7] || "0"),
      atr_stop: parseInt(r[8] || "0"),
      atr_target: parseInt(r[9] || "0"),
      buy_date: r[10] || "",
    }));

  // 매매 이력
  const historyRows = (historyRes.data.values || []).slice(1);
  const history = historyRows.map((r) => ({
    date: r[0] || "",
    code: r[1] || "",
    name: r[2] || "",
    pnl_pct: parseFloat(r[3] || "0"),
    pnl: parseInt(r[4] || "0"),
  }));

  // 오늘/이번주 실현손익 계산
  const today = new Date().toISOString().slice(0, 10);
  const dayOfWeek = new Date().getDay();
  const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
  const weekStart = new Date(Date.now() - mondayOffset * 86400000).toISOString().slice(0, 10);

  const todayPnl = history.filter((t) => t.date === today).reduce((s, t) => s + t.pnl, 0);
  const weekPnl = history.filter((t) => t.date >= weekStart).reduce((s, t) => s + t.pnl, 0);
  const totalRealized = history.reduce((s, t) => s + t.pnl, 0);

  return {
    balance: {
      ...balance,
      holdings,
    },
    history,
    today_pnl: todayPnl,
    week_pnl: weekPnl,
    total_realized: totalRealized,
    unrealized_pnl: balance.total_pnl,
  };
}
