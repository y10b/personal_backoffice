import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getThreads, saveThreads, updateThreadStatus } from "@/lib/content";
import { generateThreads } from "@/lib/gemini";

export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const status = req.nextUrl.searchParams.get("status") || undefined;
  try {
    const threads = await getThreads(status);
    return NextResponse.json({ success: true, threads });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

// 블로그 글에서 Threads 자동 생성
export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { source_type, source_id, title, html_content, count = 3 } = await req.json();
  try {
    const contents = await generateThreads(title, html_content, count);
    const ids = await saveThreads({ sourceType: source_type, sourceId: source_id, contents });
    return NextResponse.json({ success: true, thread_ids: ids, contents });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

export async function PATCH(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { id, status } = await req.json();
  try {
    await updateThreadStatus(id, status);
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
