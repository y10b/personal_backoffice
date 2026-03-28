import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getContis, updateContiStatus } from "@/lib/content";

export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const status = req.nextUrl.searchParams.get("status") || undefined;
  try {
    const contis = await getContis(status);
    return NextResponse.json({ success: true, contis });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

export async function PATCH(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { id, status } = await req.json();
  try {
    await updateContiStatus(id, status);
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
