import { NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";

export async function POST() {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const workerUrl = process.env.REEL_WORKER_URL;
  if (!workerUrl) {
    return NextResponse.json({ error: "REEL_WORKER_URL 설정 필요" }, { status: 500 });
  }

  try {
    const res = await fetch(`${workerUrl}/daily-shorts`, { method: "POST" });
    const data = await res.json();
    return NextResponse.json({ success: true, ...data });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
