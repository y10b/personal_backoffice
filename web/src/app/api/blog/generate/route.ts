import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { generateBlogPost } from "@/lib/gemini";
import { saveDraft } from "@/lib/sheets";

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { blog_type, keyword, context = "", cpc_category = "청년 지원금" } = await req.json();

  try {
    const post = await generateBlogPost(blog_type, keyword, context, cpc_category);
    const draftId = await saveDraft(post, blog_type);

    return NextResponse.json({
      success: true,
      draft_id: draftId,
      raw: post,
      message: `초안 저장 완료 (${draftId})`,
    });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
