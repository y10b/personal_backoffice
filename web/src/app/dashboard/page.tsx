"use client";

import { useSession, signOut } from "next-auth/react";
import { redirect } from "next/navigation";
import { useEffect, useState, useCallback } from "react";

type Draft = Record<string, string>;

async function api(path: string, opts: RequestInit = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || err.detail || "API 오류");
  }
  return res.json();
}

function fmt(n: number | undefined) { return (n ?? 0).toLocaleString("ko-KR"); }
function pnlColor(n: number) { return n > 0 ? "text-red-400" : n < 0 ? "text-blue-400" : "text-gray-500"; }
function pnlSign(n: number) { return n > 0 ? "+" : ""; }

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [trading, setTrading] = useState<Record<string, unknown> | null>(null);
  const [adsense, setAdsense] = useState<Record<string, unknown> | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [preview, setPreview] = useState<Draft | null>(null);

  // Generate form
  const [blogType, setBlogType] = useState("dev");
  const [keyword, setKeyword] = useState("");
  const [context, setContext] = useState("");
  const [cpcCategory, setCpcCategory] = useState("청년 지원금");
  const [generating, setGenerating] = useState(false);
  const [threadGenerating, setThreadGenerating] = useState(false);

  const loadStats = useCallback(async () => {
    try { setStats(await api("/api/dashboard")); } catch {}
  }, []);

  const loadTrading = useCallback(async () => {
    try { setTrading(await api("/api/trading")); } catch {}
  }, []);

  const loadAdsense = useCallback(async () => {
    try { setAdsense(await api("/api/adsense")); } catch {}
  }, []);

  const loadDrafts = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      const data = await api(`/api/drafts?${params}`);
      setDrafts((data.drafts || []).reverse());
    } catch {}
  }, [statusFilter]);

  useEffect(() => { loadStats(); loadTrading(); loadAdsense(); loadDrafts(); }, [loadStats, loadTrading, loadAdsense, loadDrafts]);

  if (status === "loading") return <div className="min-h-screen flex items-center justify-center text-gray-500">로딩 중...</div>;
  if (!session) redirect("/login");

  const generateDraft = async () => {
    if (!keyword.trim()) return alert("키워드를 입력하세요.");
    setGenerating(true);
    try {
      const data = await api("/api/blog/generate", {
        method: "POST",
        body: JSON.stringify({ blog_type: blogType, keyword, context, cpc_category: cpcCategory }),
      });
      alert(`초안 생성 완료! (${data.draft_id})`);
      setKeyword(""); setContext("");
      loadStats(); loadDrafts();
    } catch (e) {
      alert("생성 실패: " + (e as Error).message);
    } finally { setGenerating(false); }
  };

  const copyHtml = async (draft: Draft) => {
    try {
      await navigator.clipboard.writeText(draft["HTML본문"] || "");
      alert("HTML 복사 완료!\n\n티스토리 에디터 → HTML 모드에 붙여넣기 하세요.");
      await updateStatus(draft["ID"], "발행완료");
    } catch {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = draft["HTML본문"] || "";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      alert("HTML 복사 완료!");
    }
  };

  const copyTitle = async (draft: Draft) => {
    await navigator.clipboard.writeText(draft["제목"] || "");
    alert("제목 복사 완료!");
  };

  const copyTags = async (draft: Draft) => {
    await navigator.clipboard.writeText(draft["태그"] || "");
    alert("태그 복사 완료!");
  };


  const updateStatus = async (id: string, s: string) => {
    try {
      await api(`/api/drafts/${id}`, { method: "PATCH", body: JSON.stringify({ status: s }) });
      alert(`상태 변경: ${s}`);
      setPreview(null); loadDrafts();
    } catch (e) { alert((e as Error).message); }
  };

  const bal = (trading as Record<string, Record<string, unknown>> | null)?.balance || {};
  const holdings = (bal.holdings || []) as Record<string, unknown>[];
  const history = ((trading as Record<string, unknown[]> | null)?.history || []).slice(-10).reverse();

  const badgeClass: Record<string, string> = {
    "초안": "bg-blue-900/50 text-blue-400",
    "리뷰중": "bg-yellow-900/50 text-yellow-400",
    "수정완료": "bg-green-900/50 text-green-400",
    "발행완료": "bg-purple-900/50 text-purple-400",
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="px-8 py-5 bg-[#1a1a24] border-b border-[#2a2a3a] flex justify-between items-center">
        <h1 className="text-xl font-bold text-white">대시보드</h1>
        <div className="flex items-center gap-4">
          <a href="/content" className="text-sm text-gray-400 hover:text-white">콘텐츠</a>
          <span className="text-sm text-gray-500">{session.user?.email}</span>
          <button onClick={() => signOut()} className="text-sm text-gray-400 hover:text-white">로그아웃</button>
        </div>
      </header>

      <div className="max-w-[1200px] mx-auto p-6 space-y-6">
        {/* Blog Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
          <Card label="오늘 생성" value={String((stats as Record<string, number> | null)?.today_drafts ?? "-")} accent />
          <Card label="오늘 발행" value={String((stats as Record<string, number> | null)?.today_published ?? "-")} accent />
          <Card label="전체 초안" value={String((stats as Record<string, number> | null)?.total_drafts ?? "-")} />
          <Card label="전체 발행" value={String((stats as Record<string, number> | null)?.total_published ?? "-")} />
          <Card label="개발 블로그" value={String(((stats as Record<string, Record<string, number>> | null)?.type_counts)?.dev ?? "-")} />
          <Card label="CPC 블로그" value={String(((stats as Record<string, Record<string, number>> | null)?.type_counts)?.cpc ?? "-")} />
        </div>

        {/* Trading Section */}
        <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
          <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
            <h2 className="text-base font-semibold text-white">자동매매 (KIS)</h2>
            <button onClick={loadTrading} className="text-xs text-gray-400 border border-[#2a2a3a] px-3 py-1 rounded hover:text-white">새로고침</button>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
              <MiniCard label="총 평가금액" value={`${fmt(bal.total_eval as number)}원`} sub={`예수금: ${fmt(bal.cash as number)}원`} />
              <MiniCard label="미실현 손익" value={`${pnlSign(bal.total_pnl as number)}${fmt(bal.total_pnl as number)}원`} valueClass={pnlColor(bal.total_pnl as number)} sub={`매입: ${fmt(bal.total_buy as number)}원`} />
              <MiniCard label="오늘 실현손익" value={`${pnlSign(trading?.today_pnl as number)}${fmt(trading?.today_pnl as number)}원`} valueClass={pnlColor(trading?.today_pnl as number)} />
              <MiniCard label="이번주 실현손익" value={`${pnlSign(trading?.week_pnl as number)}${fmt(trading?.week_pnl as number)}원`} valueClass={pnlColor(trading?.week_pnl as number)} sub={`누적: ${pnlSign(trading?.total_realized as number)}${fmt(trading?.total_realized as number)}원`} />
            </div>

            {holdings.length > 0 ? (
              <table className="w-full text-sm">
                <thead><tr className="text-xs text-gray-500 border-b border-[#2a2a3a]">
                  <th className="text-left p-2">종목</th><th className="text-right p-2">수량</th><th className="text-right p-2">매수가</th>
                  <th className="text-right p-2">현재가</th><th className="text-right p-2">수익률</th><th className="text-right p-2">손익</th>
                </tr></thead>
                <tbody>{holdings.map((h, i) => (
                  <tr key={i} className="border-b border-[#1f1f2f] hover:bg-[#1f1f2f]">
                    <td className="p-2"><strong>{h.name as string}</strong><br/><span className="text-xs text-gray-600">{h.code as string}</span></td>
                    <td className="p-2 text-right">{fmt(h.qty as number)}주</td>
                    <td className="p-2 text-right">{fmt(h.buy_price as number)}</td>
                    <td className="p-2 text-right">{fmt(h.cur_price as number)}</td>
                    <td className={`p-2 text-right font-semibold ${pnlColor(h.pnl_pct as number)}`}>{pnlSign(h.pnl_pct as number)}{(h.pnl_pct as number)?.toFixed(2)}%</td>
                    <td className={`p-2 text-right ${pnlColor(h.pnl as number)}`}>{pnlSign(h.pnl as number)}{fmt(h.pnl as number)}원</td>
                  </tr>
                ))}</tbody>
              </table>
            ) : <p className="text-center text-gray-600 py-8">보유 종목이 없습니다.</p>}

            {history.length > 0 && (
              <div className="mt-4">
                <p className="text-xs text-gray-500 font-semibold mb-2">최근 매매 이력</p>
                {history.map((t, i) => (
                  <div key={i} className="flex justify-between py-2 border-b border-[#1f1f2f] text-sm">
                    <span>{(t as Record<string, unknown>).name as string} <span className="text-xs text-gray-600">{(t as Record<string, unknown>).date as string}</span></span>
                    <span className={pnlColor((t as Record<string, unknown>).pnl as number)}>{pnlSign((t as Record<string, unknown>).pnl as number)}{fmt((t as Record<string, unknown>).pnl as number)}원 ({(t as Record<string, unknown>).pnl_pct as number}%)</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* AdSense */}
        <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
          <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
            <h2 className="text-base font-semibold text-white">AdSense 수익</h2>
            <div className="flex gap-2">
              <button onClick={loadAdsense} className="text-xs text-gray-400 border border-[#2a2a3a] px-3 py-1 rounded hover:text-white">새로고침</button>
              {!adsense?.today && <a href="/api/adsense/auth" className="text-xs text-indigo-400 border border-indigo-800 px-3 py-1 rounded hover:bg-indigo-900">AdSense 연동</a>}
            </div>
          </div>
          <div className="p-5">
            {adsense?.error ? (
              <div className="text-center py-6">
                <p className="text-gray-500 text-sm mb-3">AdSense 연동이 필요합니다</p>
                <a href="/api/adsense/auth" className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">ad.seungjun73 계정으로 연동</a>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MiniCard label="오늘 수익" value={`$${((adsense?.today as Record<string, number>)?.earnings ?? 0).toFixed(2)}`} sub={`${(adsense?.today as Record<string, number>)?.page_views ?? 0} PV`} valueClass="text-emerald-400" />
                <MiniCard label="이번주 수익" value={`$${((adsense?.week as Record<string, number>)?.earnings ?? 0).toFixed(2)}`} sub={`${(adsense?.week as Record<string, number>)?.clicks ?? 0} 클릭`} valueClass="text-emerald-400" />
                <MiniCard label="이번달 수익" value={`$${((adsense?.month as Record<string, number>)?.earnings ?? 0).toFixed(2)}`} sub={`${(adsense?.month as Record<string, number>)?.page_views ?? 0} PV`} valueClass="text-emerald-400" />
                <MiniCard label="전체 누적" value={`$${((adsense?.total as Record<string, number>)?.earnings ?? 0).toFixed(2)}`} sub={`CPC $${((adsense?.total as Record<string, number>)?.cpc ?? 0).toFixed(3)}`} valueClass="text-emerald-400" />
              </div>
            )}
          </div>
        </section>

        {/* Budget */}
        <BudgetSection />

        {/* Generate */}
        <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
          <div className="px-5 py-4 border-b border-[#2a2a3a]"><h2 className="text-base font-semibold text-white">초안 생성</h2></div>
          <div className="p-5 space-y-3">
            <div className="flex gap-3 flex-wrap">
              <select value={blogType} onChange={e => setBlogType(e.target.value)} className="bg-[#0f0f13] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded-lg text-sm">
                <option value="dev">개발 블로그</option>
                <option value="cpc">CPC 블로그</option>
              </select>
              <input value={keyword} onChange={e => setKeyword(e.target.value)} placeholder="메인 키워드" className="flex-1 min-w-[200px] bg-[#0f0f13] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded-lg text-sm" />
              {blogType === "cpc" && (
                <select value={cpcCategory} onChange={e => setCpcCategory(e.target.value)} className="bg-[#0f0f13] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded-lg text-sm">
                  <option>청년 지원금</option><option>프리랜서 세금</option><option>N잡 수익</option>
                  <option>대출/금융상품</option><option>보험</option><option>청년 주거</option>
                </select>
              )}
            </div>
            <div className="flex gap-3">
              <input value={context} onChange={e => setContext(e.target.value)} placeholder="추가 컨텍스트 (선택)" className="flex-1 bg-[#0f0f13] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded-lg text-sm" />
              <button onClick={generateDraft} disabled={generating} className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:bg-gray-700 disabled:text-gray-500">
                {generating ? "생성 중..." : "초안 생성"}
              </button>
            </div>
          </div>
        </section>

        {/* Drafts */}
        <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
          <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
            <h2 className="text-base font-semibold text-white">초안 목록</h2>
            <div className="flex gap-2">
              <button onClick={loadDrafts} className="text-xs text-gray-400 border border-[#2a2a3a] px-3 py-1 rounded hover:text-white">새로고침</button>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-[#0f0f13] border border-[#2a2a3a] text-gray-300 px-2 py-1 rounded text-xs">
                <option value="">전체</option><option value="초안">초안</option><option value="수정완료">수정완료</option><option value="발행완료">발행완료</option>
              </select>
            </div>
          </div>
          <div className="p-5">
            {drafts.length === 0 ? <p className="text-center text-gray-600 py-8">초안이 없습니다.</p> : (
              <table className="w-full text-sm">
                <thead><tr className="text-xs text-gray-500 border-b border-[#2a2a3a]">
                  <th className="text-left p-2">ID</th><th className="text-left p-2">날짜</th><th className="text-left p-2">타입</th>
                  <th className="text-left p-2">제목</th><th className="text-left p-2">상태</th><th className="text-left p-2">액션</th>
                </tr></thead>
                <tbody>{drafts.map((d) => (
                  <tr key={d["ID"]} className="border-b border-[#1f1f2f] hover:bg-[#1f1f2f]">
                    <td className="p-2 text-xs text-gray-600">{d["ID"]}</td>
                    <td className="p-2">{d["날짜"]}</td>
                    <td className="p-2">{d["블로그타입"] === "dev" ? "개발" : "CPC"}</td>
                    <td className="p-2 max-w-[250px] truncate">
                      <button onClick={() => setPreview(d)} className="text-left text-indigo-400 hover:text-indigo-300 hover:underline">{d["제목"]}</button>
                    </td>
                    <td className="p-2"><span className={`px-2 py-0.5 rounded text-xs font-semibold ${badgeClass[d["상태"]] || ""}`}>{d["상태"]}</span></td>
                    <td className="p-2 space-x-1">
                      {d["상태"] !== "발행완료" && <button onClick={() => copyHtml(d)} className="text-xs text-emerald-400 border border-emerald-800 px-2 py-1 rounded hover:bg-emerald-900">HTML 복사</button>}
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            )}
          </div>
        </section>
      </div>

      {/* Preview Modal */}
      {preview && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center" onClick={() => setPreview(null)}>
          <div className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl w-[90%] max-w-[800px] max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
              <h3 className="text-white font-semibold">{preview["제목"]}</h3>
              <button onClick={() => setPreview(null)} className="text-gray-400 hover:text-white text-sm">닫기</button>
            </div>
            <div className="p-5 overflow-y-auto flex-1">
              <div className="flex gap-4 text-xs text-gray-500 mb-3 flex-wrap">
                <span>ID: {preview["ID"]}</span>
                <span>키워드: {preview["키워드"]}</span>
                <span>카테고리: {preview["카테고리"]}</span>
                <span>태그: {preview["태그"]}</span>
              </div>
              <div className="text-xs text-gray-400 bg-[#0f0f13] p-3 rounded mb-4">
                <span className="text-gray-600">메타 디스크립션:</span> {preview["메타디스크립션"]}
              </div>
              <div className="bg-white text-gray-800 p-6 rounded-lg prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: preview["HTML본문"] || "" }} />
            </div>
            <div className="px-5 py-3 border-t border-[#2a2a3a] flex gap-2 justify-between">
              <div className="flex gap-2">
                <button onClick={() => copyTitle(preview)} className="text-xs border border-[#2a2a3a] text-gray-400 px-3 py-1.5 rounded hover:text-white">제목 복사</button>
                <button onClick={() => copyTags(preview)} className="text-xs border border-[#2a2a3a] text-gray-400 px-3 py-1.5 rounded hover:text-white">태그 복사</button>
                <button disabled={threadGenerating} onClick={async () => {
                  setThreadGenerating(true);
                  try {
                    await api("/api/threads", {
                      method: "POST",
                      body: JSON.stringify({ source_type: "블로그", source_id: preview["ID"], title: preview["제목"], html_content: preview["HTML본문"] }),
                    });
                    alert("Threads 3개 생성 완료! 콘텐츠 페이지에서 확인하세요.");
                  } catch (e) { alert((e as Error).message); }
                  finally { setThreadGenerating(false); }
                }} className="text-xs text-pink-400 border border-pink-800 px-3 py-1.5 rounded hover:bg-pink-900 disabled:opacity-50">{threadGenerating ? "생성중..." : "Threads 생성"}</button>
              </div>
              <div className="flex gap-2">
                {preview["상태"] !== "발행완료" && (
                  <>
                    <button onClick={() => copyHtml(preview)} className="text-xs bg-emerald-700 text-white px-3 py-1.5 rounded hover:bg-emerald-600 font-semibold">HTML 복사</button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Card({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`bg-[#1a1a24] border rounded-xl p-5 ${accent ? "border-indigo-600" : "border-[#2a2a3a]"}`}>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${accent ? "text-indigo-400" : "text-white"}`}>{value}</div>
    </div>
  );
}

function MiniCard({ label, value, sub, valueClass }: { label: string; value: string; sub?: string; valueClass?: string }) {
  return (
    <div className="bg-[#13131b] border border-[#2a2a3a] rounded-lg p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${valueClass || "text-white"}`}>{value}</div>
      {sub && <div className="text-xs text-gray-600 mt-1">{sub}</div>}
    </div>
  );
}

// ── 가계부 섹션 ──

type BudgetData = {
  income?: { total: number; items: { name: string; amount: number; memo: string }[] };
  fixed?: { total: number; items: { name: string; amount: number; memo: string }[] };
  variable?: { total: number; byCategory: Record<string, number> };
  total_spent?: number;
  remaining?: number;
  recommendation?: {
    savings: number; invest: number; emergency: number; spending: number;
    actual_remaining: number; savings_pct: number; invest_pct: number; emergency_pct: number;
  };
};

const GOAL_AMOUNT = 100_000_000; // 1억
const GOAL_YEARS = 5;
const GOAL_MONTHS = GOAL_YEARS * 12;

function BudgetSection() {
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [tradingData, setTradingData] = useState<Record<string, unknown> | null>(null);
  const [showAdd, setShowAdd] = useState<"income" | "fixed" | "expense" | null>(null);
  const [form, setForm] = useState({ name: "", amount: "", category: "식비", memo: "" });
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const [b, t] = await Promise.all([api("/api/budget"), api("/api/trading")]);
      setBudget(b);
      setTradingData(t);
    } catch {}
  }, []);

  useEffect(() => { load(); }, [load]);

  const addSetting = async (type: string) => {
    if (!form.name || !form.amount) return;
    setLoading(true);
    try {
      await api("/api/budget/settings", {
        method: "POST",
        body: JSON.stringify({ name: form.name, type, amount: parseInt(form.amount), memo: form.memo }),
      });
      setForm({ name: "", amount: "", category: "식비", memo: "" });
      setShowAdd(null);
      load();
    } catch (e) { alert((e as Error).message); }
    finally { setLoading(false); }
  };

  const addExpense = async () => {
    if (!form.name || !form.amount) return;
    setLoading(true);
    try {
      await api("/api/budget/expense", {
        method: "POST",
        body: JSON.stringify({
          date: new Date().toISOString().slice(0, 10),
          category: form.category, name: form.name,
          amount: parseInt(form.amount), memo: form.memo,
        }),
      });
      setForm({ name: "", amount: "", category: "식비", memo: "" });
      setShowAdd(null);
      load();
    } catch (e) { alert((e as Error).message); }
    finally { setLoading(false); }
  };

  const totalIncome = budget?.income?.total || 0;
  const monthlySaving = budget?.remaining || 0;

  // 자동매매 수익률 계산 (월간 환산)
  const totalBuy = (tradingData?.balance as Record<string, number>)?.total_buy || 0;
  const unrealizedPnl = (tradingData?.unrealized_pnl as number) || 0;
  const totalRealized = (tradingData?.total_realized as number) || 0;
  const totalTradingPnl = unrealizedPnl + totalRealized;
  const monthlyReturnPct = totalBuy > 0 ? (totalTradingPnl / totalBuy) * 100 : 0;
  // 보수적으로 월 수익률 추정 (연 환산 후 다시 월로)
  const annualReturnPct = monthlyReturnPct * 12;
  const monthlyR = Math.max(0, annualReturnPct / 100 / 12); // 월 수익률 (소수)

  // 수익률 반영한 월 목표 계산 (적립식 복리)
  // FV = PMT * ((1+r)^n - 1) / r → PMT = FV * r / ((1+r)^n - 1)
  const monthlyGoalNoReturn = Math.ceil(GOAL_AMOUNT / GOAL_MONTHS);
  const monthlyGoalWithReturn = monthlyR > 0
    ? Math.ceil(GOAL_AMOUNT * monthlyR / (Math.pow(1 + monthlyR, GOAL_MONTHS) - 1))
    : monthlyGoalNoReturn;

  // 현재 페이스로 예상 (복리 반영)
  const projectedTotal = monthlyR > 0
    ? Math.round(monthlySaving * (Math.pow(1 + monthlyR, GOAL_MONTHS) - 1) / monthlyR)
    : monthlySaving * GOAL_MONTHS;

  // 현재 페이스로 1억까지 걸리는 시간
  let projectedYears = "∞";
  if (monthlySaving > 0) {
    if (monthlyR > 0) {
      // n = log(1 + FV*r/PMT) / log(1+r) → 월 수
      const months = Math.log(1 + GOAL_AMOUNT * monthlyR / monthlySaving) / Math.log(1 + monthlyR);
      projectedYears = (months / 12).toFixed(1);
    } else {
      projectedYears = (GOAL_AMOUNT / monthlySaving / 12).toFixed(1);
    }
  }

  const monthlyGap = monthlySaving - monthlyGoalWithReturn;

  return (
    <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
      <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
        <h2 className="text-base font-semibold text-white">가계부</h2>
        <div className="flex gap-2">
          <button onClick={() => setShowAdd("income")} className="text-xs text-blue-400 border border-blue-800 px-2 py-1 rounded hover:bg-blue-900">+ 수입</button>
          <button onClick={() => setShowAdd("fixed")} className="text-xs text-orange-400 border border-orange-800 px-2 py-1 rounded hover:bg-orange-900">+ 고정지출</button>
          <button onClick={() => setShowAdd("expense")} className="text-xs text-pink-400 border border-pink-800 px-2 py-1 rounded hover:bg-pink-900">+ 지출</button>
          <button onClick={load} className="text-xs text-gray-400 border border-[#2a2a3a] px-2 py-1 rounded hover:text-white">새로고침</button>
        </div>
      </div>
      <div className="p-5 space-y-5">
        {/* 입력 폼 */}
        {showAdd && (
          <div className="bg-[#0f0f13] p-4 rounded-lg space-y-3">
            <div className="flex gap-3 flex-wrap">
              {showAdd === "expense" && (
                <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} className="bg-[#1a1a24] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded text-sm">
                  <option>식비</option><option>교통</option><option>문화</option><option>쇼핑</option><option>생활</option><option>기타</option>
                </select>
              )}
              <input placeholder="항목명" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="flex-1 min-w-[120px] bg-[#1a1a24] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded text-sm" />
              <input placeholder="금액" type="number" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} className="w-[130px] bg-[#1a1a24] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded text-sm" />
              <input placeholder="메모 (선택)" value={form.memo} onChange={e => setForm({ ...form, memo: e.target.value })} className="flex-1 min-w-[100px] bg-[#1a1a24] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded text-sm" />
              <button disabled={loading} onClick={() => showAdd === "expense" ? addExpense() : addSetting(showAdd === "income" ? "수입" : "고정지출")} className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-semibold hover:bg-indigo-700 disabled:bg-gray-700">{loading ? "..." : "추가"}</button>
              <button onClick={() => setShowAdd(null)} className="text-gray-500 text-sm hover:text-white">취소</button>
            </div>
          </div>
        )}

        {/* 요약 카드 */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <MiniCard label="총 수입" value={`${fmt(totalIncome)}원`} valueClass="text-blue-400" />
          <MiniCard label="고정지출" value={`${fmt(budget?.fixed?.total)}원`} valueClass="text-orange-400" />
          <MiniCard label="변동지출" value={`${fmt(budget?.variable?.total)}원`} valueClass="text-pink-400" />
          <MiniCard label="이번달 잔액" value={`${fmt(budget?.remaining)}원`} valueClass={monthlySaving >= 0 ? "text-emerald-400" : "text-red-400"} />
          <MiniCard label="월 목표" value={`${fmt(monthlyGoalWithReturn)}원`} sub={annualReturnPct > 0 ? `수익률 ${annualReturnPct.toFixed(1)}% 반영` : "5년 1억 기준"} />
        </div>

        {/* 1억 목표 계산기 */}
        {totalIncome > 0 && (
          <div className="bg-[#13131b] border border-[#2a2a3a] rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <p className="text-sm font-semibold text-white">5년 1억 목표</p>
              {annualReturnPct > 0 && <span className="text-xs text-indigo-400 bg-indigo-900/30 px-2 py-0.5 rounded">자동매매 연 {annualReturnPct.toFixed(1)}% 반영</span>}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <span className="text-gray-500">월 목표:</span>
                <span className="text-white ml-2 font-semibold">{fmt(monthlyGoalWithReturn)}원</span>
                {monthlyGoalWithReturn < monthlyGoalNoReturn && <div className="text-xs text-gray-600 mt-0.5">저축만: {fmt(monthlyGoalNoReturn)}원</div>}
              </div>
              <div>
                <span className="text-gray-500">현재 가능:</span>
                <span className={`ml-2 font-semibold ${monthlySaving >= monthlyGoalWithReturn ? "text-emerald-400" : "text-red-400"}`}>{fmt(monthlySaving)}원</span>
              </div>
              <div>
                <span className="text-gray-500">차이:</span>
                <span className={`ml-2 font-semibold ${monthlyGap >= 0 ? "text-emerald-400" : "text-red-400"}`}>{monthlyGap >= 0 ? "+" : ""}{fmt(monthlyGap)}원</span>
              </div>
              <div>
                <span className="text-gray-500">예상 달성:</span>
                <span className={`ml-2 font-semibold ${parseFloat(projectedYears) <= 5 ? "text-emerald-400" : "text-amber-400"}`}>{projectedYears}년</span>
              </div>
            </div>

            {/* 프로그레스 바 */}
            <div className="mt-3">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>5년 예상 저축: {fmt(projectedTotal)}원</span>
                <span>목표: {fmt(GOAL_AMOUNT)}원</span>
              </div>
              <div className="h-3 bg-[#2a2a3a] rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${projectedTotal >= GOAL_AMOUNT ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: `${Math.min(100, projectedTotal / GOAL_AMOUNT * 100)}%` }} />
              </div>
            </div>

            {/* 배분 추천 */}
            {budget?.recommendation && monthlySaving > 0 && (
              <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
                <div className="bg-[#0f0f13] p-2 rounded text-center">
                  <div className="text-gray-500">저축 ({budget.recommendation.savings_pct}%)</div>
                  <div className="text-emerald-400 font-semibold">{fmt(budget.recommendation.savings)}원</div>
                </div>
                <div className="bg-[#0f0f13] p-2 rounded text-center">
                  <div className="text-gray-500">투자 ({budget.recommendation.invest_pct}%)</div>
                  <div className="text-blue-400 font-semibold">{fmt(budget.recommendation.invest)}원</div>
                </div>
                <div className="bg-[#0f0f13] p-2 rounded text-center">
                  <div className="text-gray-500">비상금 ({budget.recommendation.emergency_pct}%)</div>
                  <div className="text-amber-400 font-semibold">{fmt(budget.recommendation.emergency)}원</div>
                </div>
                <div className="bg-[#0f0f13] p-2 rounded text-center">
                  <div className="text-gray-500">생활비</div>
                  <div className="text-gray-300 font-semibold">{fmt(budget.recommendation.spending)}원</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 수입/고정지출 상세 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {budget?.income?.items && budget.income.items.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 font-semibold mb-2">수입</p>
              {budget.income.items.map((item, i) => (
                <div key={i} className="flex justify-between py-1.5 border-b border-[#1f1f2f] text-sm">
                  <span>{item.name} <span className="text-xs text-gray-600">{item.memo}</span></span>
                  <span className="text-blue-400">{fmt(item.amount)}원</span>
                </div>
              ))}
            </div>
          )}
          {budget?.fixed?.items && budget.fixed.items.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 font-semibold mb-2">고정지출</p>
              {budget.fixed.items.map((item, i) => (
                <div key={i} className="flex justify-between py-1.5 border-b border-[#1f1f2f] text-sm">
                  <span>{item.name} <span className="text-xs text-gray-600">{item.memo}</span></span>
                  <span className="text-orange-400">{fmt(item.amount)}원</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 카테고리별 변동지출 */}
        {budget?.variable?.byCategory && Object.keys(budget.variable.byCategory).length > 0 && (
          <div>
            <p className="text-xs text-gray-500 font-semibold mb-2">이번달 지출 (카테고리별)</p>
            <div className="flex gap-3 flex-wrap">
              {Object.entries(budget.variable.byCategory).map(([cat, amt]) => (
                <div key={cat} className="bg-[#0f0f13] px-3 py-2 rounded text-sm">
                  <span className="text-gray-400">{cat}</span>
                  <span className="text-pink-400 ml-2 font-semibold">{fmt(amt as number)}원</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
