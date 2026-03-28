import { NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getTradingDashboard } from "@/lib/trading";

export async function GET() {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  try {
    const data = await getTradingDashboard();
    return NextResponse.json({ success: true, ...data });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
