import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getDrafts } from "@/lib/sheets";

export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const status = req.nextUrl.searchParams.get("status") || undefined;
  const date = req.nextUrl.searchParams.get("date") || undefined;

  try {
    const drafts = await getDrafts(status, date);
    return NextResponse.json({ success: true, drafts, count: drafts.length });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
