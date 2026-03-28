import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getDraftById, recordPublish } from "@/lib/sheets";
import { getBlogName, postToTistory } from "@/lib/tistory";

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { draft_id, visibility = 0 } = await req.json();

  try {
    const draft = await getDraftById(draft_id);
    if (!draft) return NextResponse.json({ error: "Not found" }, { status: 404 });
    if (!["초안", "수정완료"].includes(draft["상태"])) {
      return NextResponse.json({ error: `발행 불가 상태: ${draft["상태"]}` }, { status: 400 });
    }

    const blogType = draft["블로그타입"] || "dev";
    const blogName = getBlogName(blogType);

    const postId = await postToTistory(
      {
        title: draft["제목"],
        html_content: draft["HTML본문"],
        tags: (draft["태그"] || "").split(",").map((t: string) => t.trim()),
      },
      blogName,
      visibility,
    );

    await recordPublish(draft_id, blogType, blogName, draft["제목"], draft["키워드"], String(postId));

    return NextResponse.json({ success: true, post_id: postId, message: `발행 완료! (${postId})` });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
