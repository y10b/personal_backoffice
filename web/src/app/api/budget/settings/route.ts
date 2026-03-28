import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { getBudgetSettings, saveBudgetSetting, deleteBudgetSetting } from "@/lib/budget";

export async function GET() {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  try {
    const settings = await getBudgetSettings();
    return NextResponse.json({ success: true, ...settings });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { name, type, amount, memo = "" } = await req.json();
  try {
    await saveBudgetSetting(name, type, amount, memo);
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { name, type } = await req.json();
  try {
    await deleteBudgetSetting(name, type);
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
