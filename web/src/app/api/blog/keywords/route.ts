import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { suggestKeywords } from "@/lib/gemini";

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { blog_type = "dev", topic_hint = "" } = await req.json();

  try {
    const keywords = await suggestKeywords(blog_type, topic_hint);
    return NextResponse.json({ success: true, keywords });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
