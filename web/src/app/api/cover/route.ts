import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { generateDevCover, generateCpcCover } from "@/lib/cover";

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { blog_type, title, keywords = [], date, cpc_category = "" } = await req.json();

  const html = blog_type === "dev"
    ? generateDevCover(title, keywords, date || new Date().toISOString().slice(0, 10))
    : generateCpcCover(title, keywords, date || new Date().toISOString().slice(0, 10), cpc_category);

  return new NextResponse(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
