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

// ── 설정 (수입/고정지출/저축비율) ──

export async function getBudgetSettings() {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "가계부-설정!A:D",
  });
  const rows = (res.data.values || []).slice(1);

  const income: { name: string; amount: number; memo: string }[] = [];
  const fixedExpenses: { name: string; amount: number; memo: string }[] = [];
  let savingsPct = 30;
  let investPct = 20;
  let emergencyPct = 10;

  for (const r of rows) {
    const [name, type, amount, memo] = r;
    if (type === "수입") income.push({ name, amount: parseInt(amount || "0"), memo: memo || "" });
    if (type === "고정지출") fixedExpenses.push({ name, amount: parseInt(amount || "0"), memo: memo || "" });
    if (type === "저축비율" && name === "저축") savingsPct = parseFloat(amount || "30");
    if (type === "저축비율" && name === "투자") investPct = parseFloat(amount || "20");
    if (type === "저축비율" && name === "비상금") emergencyPct = parseFloat(amount || "10");
  }

  return { income, fixedExpenses, savingsPct, investPct, emergencyPct };
}

export async function saveBudgetSetting(name: string, type: string, amount: number, memo: string) {
  const sheets = getSheets();

  // 같은 이름+타입이 있으면 업데이트, 없으면 추가
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "가계부-설정!A:D",
  });
  const rows = res.data.values || [];
  let found = false;
  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] === name && rows[i][1] === type) {
      await sheets.spreadsheets.values.update({
        spreadsheetId: SHEET_ID(),
        range: `가계부-설정!A${i + 1}:D${i + 1}`,
        valueInputOption: "RAW",
        requestBody: { values: [[name, type, amount, memo]] },
      });
      found = true;
      break;
    }
  }

  if (!found) {
    await sheets.spreadsheets.values.append({
      spreadsheetId: SHEET_ID(),
      range: "가계부-설정!A:D",
      valueInputOption: "RAW",
      requestBody: { values: [[name, type, amount, memo]] },
    });
  }
}

export async function deleteBudgetSetting(name: string, type: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "가계부-설정!A:D",
  });
  const rows = res.data.values || [];
  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] === name && rows[i][1] === type) {
      await sheets.spreadsheets.values.update({
        spreadsheetId: SHEET_ID(),
        range: `가계부-설정!A${i + 1}:D${i + 1}`,
        valueInputOption: "RAW",
        requestBody: { values: [["", "", "", ""]] },
      });
      break;
    }
  }
}

// ── 지출 ──

export async function getExpenses(month?: string) {
  const sheets = getSheets();
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: SHEET_ID(),
    range: "가계부-지출!A:E",
  });
  let rows = (res.data.values || []).slice(1)
    .filter((r) => r[0])
    .map((r) => ({
      date: r[0] || "",
      category: r[1] || "",
      name: r[2] || "",
      amount: parseInt(r[3] || "0"),
      memo: r[4] || "",
    }));

  if (month) {
    rows = rows.filter((r) => r.date.startsWith(month));
  }

  return rows;
}

export async function addExpense(date: string, category: string, name: string, amount: number, memo: string) {
  const sheets = getSheets();
  await sheets.spreadsheets.values.append({
    spreadsheetId: SHEET_ID(),
    range: "가계부-지출!A:E",
    valueInputOption: "RAW",
    requestBody: { values: [[date, category, name, amount, memo]] },
  });
}

// ── 요약 계산 ──

export async function getBudgetSummary(month?: string) {
  const targetMonth = month || new Date().toISOString().slice(0, 7);
  const [settings, expenses] = await Promise.all([
    getBudgetSettings(),
    getExpenses(targetMonth),
  ]);

  const totalIncome = settings.income.reduce((s, i) => s + i.amount, 0);
  const totalFixed = settings.fixedExpenses.reduce((s, e) => s + e.amount, 0);
  const totalVariable = expenses.reduce((s, e) => s + e.amount, 0);
  const totalSpent = totalFixed + totalVariable;
  const remaining = totalIncome - totalSpent;

  // 카테고리별 지출
  const byCategory: Record<string, number> = {};
  for (const e of expenses) {
    byCategory[e.category] = (byCategory[e.category] || 0) + e.amount;
  }

  // 남은 금액 배분 추천
  const disposable = totalIncome - totalFixed;
  const recommendSavings = Math.round(disposable * settings.savingsPct / 100);
  const recommendInvest = Math.round(disposable * settings.investPct / 100);
  const recommendEmergency = Math.round(disposable * settings.emergencyPct / 100);
  const recommendSpending = disposable - recommendSavings - recommendInvest - recommendEmergency;

  return {
    month: targetMonth,
    income: { total: totalIncome, items: settings.income },
    fixed: { total: totalFixed, items: settings.fixedExpenses },
    variable: { total: totalVariable, items: expenses, byCategory },
    total_spent: totalSpent,
    remaining,
    recommendation: {
      savings: recommendSavings,
      invest: recommendInvest,
      emergency: recommendEmergency,
      spending: recommendSpending,
      actual_remaining: remaining,
      savings_pct: settings.savingsPct,
      invest_pct: settings.investPct,
      emergency_pct: settings.emergencyPct,
    },
  };
}
