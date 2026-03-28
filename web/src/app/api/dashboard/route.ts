import { NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getDashboardStats } from "@/lib/sheets";

export async function GET() {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  try {
    const stats = await getDashboardStats();
    return NextResponse.json({ success: true, ...stats });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
