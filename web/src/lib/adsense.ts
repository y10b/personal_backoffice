import { google } from "googleapis";

function getOAuth2Client() {
  return new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID!,
    process.env.GOOGLE_CLIENT_SECRET!,
  );
}

function getAuthenticatedClient() {
  const token = process.env.ADSENSE_REFRESH_TOKEN;
  if (!token) throw new Error("ADSENSE_REFRESH_TOKEN 설정 필요");

  const oauth2 = getOAuth2Client();
  oauth2.setCredentials({ refresh_token: token });
  return oauth2;
}

export function getAdSenseAuthUrl(redirectUri: string) {
  const oauth2 = getOAuth2Client();
  return oauth2.generateAuthUrl({
    access_type: "offline",
    prompt: "consent select_account",
    redirect_uri: redirectUri,
    scope: ["https://www.googleapis.com/auth/adsense.readonly"],
    login_hint: "ad.seungjun73@gmail.com",
  });
}

export async function exchangeAdSenseCode(code: string, redirectUri: string) {
  const oauth2 = getOAuth2Client();
  const { tokens } = await oauth2.getToken({ code, redirect_uri: redirectUri });
  return tokens.refresh_token || "";
}

export async function getAdSenseReport() {
  const auth = getAuthenticatedClient();
  const adsense = google.adsense({ version: "v2", auth });

  // 계정 목록 조회
  const accounts = await adsense.accounts.list();
  const accountId = accounts.data.accounts?.[0]?.name;
  if (!accountId) throw new Error("AdSense 계정을 찾을 수 없습니다.");

  const today = new Date();
  const todayStr = formatDate(today);

  // 이번주 월요일
  const dayOfWeek = today.getDay();
  const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
  const monday = new Date(today.getTime() - mondayOffset * 86400000);
  const mondayStr = formatDate(monday);

  // 이번달 1일
  const monthStart = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-01`;

  // 전체 누적 (계정 생성일부터)
  const totalStart = "2024-04-30";

  const [todayReport, weekReport, monthReport, totalReport] = await Promise.all([
    fetchReport(adsense, accountId, todayStr, todayStr),
    fetchReport(adsense, accountId, mondayStr, todayStr),
    fetchReport(adsense, accountId, monthStart, todayStr),
    fetchReport(adsense, accountId, totalStart, todayStr),
  ]);

  return {
    today: todayReport,
    week: weekReport,
    month: monthReport,
    total: totalReport,
    currency: "USD",
  };
}

async function fetchReport(
  adsense: ReturnType<typeof google.adsense>,
  accountId: string,
  startDate: string,
  endDate: string,
) {
  try {
    const res = await adsense.accounts.reports.generate({
      account: accountId,
      dateRange: "CUSTOM",
      "startDate.year": parseInt(startDate.split("-")[0]),
      "startDate.month": parseInt(startDate.split("-")[1]),
      "startDate.day": parseInt(startDate.split("-")[2]),
      "endDate.year": parseInt(endDate.split("-")[0]),
      "endDate.month": parseInt(endDate.split("-")[1]),
      "endDate.day": parseInt(endDate.split("-")[2]),
      metrics: [
        "ESTIMATED_EARNINGS",
        "PAGE_VIEWS",
        "CLICKS",
        "COST_PER_CLICK",
      ],
    });

    const row = res.data.totals?.cells || [];
    return {
      earnings: parseFloat(row[0]?.value || "0"),
      page_views: parseInt(row[1]?.value || "0"),
      clicks: parseInt(row[2]?.value || "0"),
      cpc: parseFloat(row[3]?.value || "0"),
    };
  } catch {
    return { earnings: 0, page_views: 0, clicks: 0, cpc: 0 };
  }
}

function formatDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
