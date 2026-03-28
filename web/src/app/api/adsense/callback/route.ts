import { NextRequest, NextResponse } from "next/server";
import { exchangeAdSenseCode } from "@/lib/adsense";

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  if (!code) {
    return new NextResponse("인증 코드가 없습니다.", { status: 400 });
  }

  try {
    const origin = req.nextUrl.origin;
    const redirectUri = `${origin}/api/adsense/callback`;
    const refreshToken = await exchangeAdSenseCode(code, redirectUri);

    return new NextResponse(
      `<html><body style="background:#0f0f13;color:#e0e0e0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
        <div style="text-align:center;max-width:600px;">
          <h2>AdSense 연동 완료!</h2>
          <p>Vercel 환경변수에 추가하세요:</p>
          <code style="background:#1a1a24;padding:12px;border-radius:8px;display:block;word-break:break-all;margin:16px 0;">ADSENSE_REFRESH_TOKEN=${refreshToken}</code>
          <p style="color:#888;font-size:14px;">.env.local에도 추가 후 서버 재시작</p>
          <a href="/dashboard" style="color:#818cf8;">대시보드로 돌아가기</a>
        </div>
      </body></html>`,
      { headers: { "Content-Type": "text/html" } }
    );
  } catch (e) {
    return new NextResponse(`인증 실패: ${e}`, { status: 500 });
  }
}
