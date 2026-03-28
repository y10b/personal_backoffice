import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { createContiRequest, getContiRequests } from "@/lib/conti-request";

export async function GET() {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  try {
    const requests = await getContiRequests();
    return NextResponse.json({ success: true, requests });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { type, url, story, content_type } = await req.json();
  try {
    const reqId = await createContiRequest({
      type: type || (url ? "url" : "story"),
      url,
      story,
      contentType: content_type || "알바 썰",
    });
    return NextResponse.json({ success: true, request_id: reqId, message: "요청 접수! 1~2분 후 콘텐츠 페이지에서 확인하세요." });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
