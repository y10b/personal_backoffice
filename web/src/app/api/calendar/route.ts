import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getCalendarData } from "@/lib/content";

export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const month = req.nextUrl.searchParams.get("month") || new Date().toISOString().slice(0, 7);
  try {
    const items = await getCalendarData(month);
    return NextResponse.json({ success: true, items, month });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
