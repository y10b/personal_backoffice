import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { conti_id, conti_json, voice } = await req.json();

  const workerUrl = process.env.REEL_WORKER_URL;
  if (!workerUrl) {
    return NextResponse.json({ error: "REEL_WORKER_URL 설정 필요" }, { status: 500 });
  }

  try {
    const res = await fetch(`${workerUrl}/assemble`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conti_id, conti_json, voice }),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json({ error: data.error || "조립 실패" }, { status: 500 });
    }

    return NextResponse.json({ success: true, ...data });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
