import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/api-auth";
import { addExpense, getExpenses } from "@/lib/budget";

export async function GET(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const month = req.nextUrl.searchParams.get("month") || undefined;
  try {
    const expenses = await getExpenses(month);
    return NextResponse.json({ success: true, expenses });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const authErr = await requireAuth();
  if (authErr) return authErr;

  const { date, category, name, amount, memo = "" } = await req.json();
  try {
    await addExpense(date, category, name, amount, memo);
    return NextResponse.json({ success: true });
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}
