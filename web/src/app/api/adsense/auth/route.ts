import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getAdSenseAuthUrl } from "@/lib/adsense";

export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const origin = req.nextUrl.origin;
  const redirectUri = `${origin}/api/adsense/callback`;
  const url = getAdSenseAuthUrl(redirectUri);

  return NextResponse.redirect(url);
}
