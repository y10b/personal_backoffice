import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getBudgetSummary } from "@/lib/budget";

export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const month = req.nextUrl.searchParams.get("month") || undefined;
  try {
    const summary = await getBudgetSummary(month);
    return NextResponse.json({ success: true, ...summary });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
