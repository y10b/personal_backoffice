import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";

const WORKER = () => process.env.REEL_WORKER_URL!;

// 씬 파일 상태 조회
export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const contiId = req.nextUrl.searchParams.get("conti_id") || "";
  const res = await fetch(`${WORKER()}/scenes/${contiId}`);
  return NextResponse.json(await res.json());
}

// 씬 파일 업로드 (프록시)
export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const formData = await req.formData();
  const contiId = formData.get("conti_id") as string;

  const res = await fetch(`${WORKER()}/scenes/${contiId}/upload`, {
    method: "POST",
    body: formData,
  });

  return NextResponse.json(await res.json());
}
