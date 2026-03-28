import { NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getAdSenseReport } from "@/lib/adsense";

export async function GET() {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  try {
    const report = await getAdSenseReport();
    return NextResponse.json({ success: true, ...report });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
