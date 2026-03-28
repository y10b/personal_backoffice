"use client";

import { useSession } from "next-auth/react";
import { redirect } from "next/navigation";
import { useEffect, useState, useCallback } from "react";

type CalendarItem = { date: string; type: "blog" | "reels" | "threads"; title: string; status: string; id: string; blogType?: string };
type ThreadItem = Record<string, string>;
type ContiItem = Record<string, string>;

async function api(path: string, opts: RequestInit = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "API 오류");
  }
  return res.json();
}

function fmt(n: number | undefined) { return (n ?? 0).toLocaleString("ko-KR"); }

const TYPE_COLORS = {
  blog: { bg: "bg-blue-900/40", text: "text-blue-400", label: "블로그" },
  reels: { bg: "bg-purple-900/40", text: "text-purple-400", label: "릴스" },
  threads: { bg: "bg-pink-900/40", text: "text-pink-400", label: "쓰레드" },
};

const STATUS_COLORS: Record<string, string> = {
  "초안": "text-blue-400",
  "촬영중": "text-yellow-400",
  "편집중": "text-orange-400",
  "수정완료": "text-green-400",
  "발행완료": "text-purple-400",
};

export default function ContentPage() {
  const { data: session, status } = useSession();
  const [tab, setTab] = useState<"calendar" | "reels" | "threads">("calendar");
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [calendar, setCalendar] = useState<CalendarItem[]>([]);
  const [contis, setContis] = useState<ContiItem[]>([]);
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [threadPreview, setThreadPreview] = useState<ThreadItem | null>(null);
  const [generating, setGenerating] = useState(false);
  const [reelForm, setReelForm] = useState({ url: "", story: "", contentType: "알바 썰" });
  const [reelRequesting, setReelRequesting] = useState(false);

  const loadCalendar = useCallback(async () => {
    try { const d = await api(`/api/calendar?month=${month}`); setCalendar(d.items || []); } catch {}
  }, [month]);

  const loadContis = useCallback(async () => {
    try { const d = await api("/api/contis"); setContis(d.contis || []); } catch {}
  }, []);

  const loadThreads = useCallback(async () => {
    try { const d = await api("/api/threads"); setThreads(d.threads || []); } catch {}
  }, []);

  useEffect(() => {
    if (tab === "calendar") loadCalendar();
    if (tab === "reels") loadContis();
    if (tab === "threads") loadThreads();
  }, [tab, loadCalendar, loadContis, loadThreads]);

  if (status === "loading") return <div className="min-h-screen flex items-center justify-center text-gray-500">로딩 중...</div>;
  if (!session) redirect("/login");

  // Calendar grid
  const daysInMonth = new Date(parseInt(month.split("-")[0]), parseInt(month.split("-")[1]), 0).getDate();
  const firstDay = new Date(parseInt(month.split("-")[0]), parseInt(month.split("-")[1]) - 1, 1).getDay();
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const calendarByDate: Record<string, CalendarItem[]> = {};
  for (const item of calendar) {
    const day = item.date;
    if (!calendarByDate[day]) calendarByDate[day] = [];
    calendarByDate[day].push(item);
  }

  const prevMonth = () => {
    const d = new Date(month + "-01");
    d.setMonth(d.getMonth() - 1);
    setMonth(d.toISOString().slice(0, 7));
  };
  const nextMonth = () => {
    const d = new Date(month + "-01");
    d.setMonth(d.getMonth() + 1);
    setMonth(d.toISOString().slice(0, 7));
  };

  const copyThread = async (content: string) => {
    await navigator.clipboard.writeText(content);
    alert("복사 완료! Threads에 붙여넣기 하세요.");
  };

  const generateFromDraft = async (draftId: string, title: string, html: string) => {
    setGenerating(true);
    try {
      await api("/api/threads", {
        method: "POST",
        body: JSON.stringify({ source_type: "블로그", source_id: draftId, title, html_content: html, count: 3 }),
      });
      alert("Threads 글 3개 생성 완료!");
      loadThreads();
      setTab("threads");
    } catch (e) { alert((e as Error).message); }
    finally { setGenerating(false); }
  };

  // 이번달 통계
  const blogCount = calendar.filter((c) => c.type === "blog").length;
  const reelsCount = calendar.filter((c) => c.type === "reels").length;
  const threadsCount = calendar.filter((c) => c.type === "threads").length;

  return (
    <div className="min-h-screen">
      <header className="px-8 py-5 bg-[#1a1a24] border-b border-[#2a2a3a] flex justify-between items-center">
        <h1 className="text-xl font-bold text-white">콘텐츠</h1>
        <div className="flex gap-3">
          <a href="/dashboard" className="text-sm text-gray-400 hover:text-white">대시보드</a>
          <a href="/content" className="text-sm text-white bg-[#2a2a3a] px-3 py-1 rounded">콘텐츠</a>
        </div>
      </header>

      <div className="max-w-[1200px] mx-auto p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl p-5 text-center">
            <div className="text-xs text-gray-500 mb-1">이번달 블로그</div>
            <div className="text-2xl font-bold text-blue-400">{blogCount}</div>
          </div>
          <div className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl p-5 text-center">
            <div className="text-xs text-gray-500 mb-1">이번달 릴스</div>
            <div className="text-2xl font-bold text-purple-400">{reelsCount}</div>
          </div>
          <div className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl p-5 text-center">
            <div className="text-xs text-gray-500 mb-1">이번달 쓰레드</div>
            <div className="text-2xl font-bold text-pink-400">{threadsCount}</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          {(["calendar", "reels", "threads"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 rounded-lg text-sm font-semibold ${tab === t ? "bg-indigo-600 text-white" : "bg-[#1a1a24] text-gray-400 hover:text-white"}`}>
              {{ calendar: "캘린더", reels: "릴스/쇼츠", threads: "쓰레드" }[t]}
            </button>
          ))}
        </div>

        {/* Calendar Tab */}
        {tab === "calendar" && (
          <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
            <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
              <button onClick={prevMonth} className="text-gray-400 hover:text-white">&lt;</button>
              <h2 className="text-base font-semibold text-white">{month}</h2>
              <button onClick={nextMonth} className="text-gray-400 hover:text-white">&gt;</button>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-7 gap-1 text-center text-xs text-gray-500 mb-2">
                {["일", "월", "화", "수", "목", "금", "토"].map((d) => <div key={d}>{d}</div>)}
              </div>
              <div className="grid grid-cols-7 gap-1">
                {Array.from({ length: firstDay }).map((_, i) => <div key={`e${i}`} />)}
                {days.map((day) => {
                  const dateStr = `${month}-${String(day).padStart(2, "0")}`;
                  const items = calendarByDate[dateStr] || [];
                  const isToday = dateStr === new Date().toISOString().slice(0, 10);
                  return (
                    <div key={day} className={`min-h-[80px] p-1 rounded border ${isToday ? "border-indigo-600" : "border-[#1f1f2f]"}`}>
                      <div className={`text-xs mb-1 ${isToday ? "text-indigo-400 font-bold" : "text-gray-500"}`}>{day}</div>
                      {items.map((item, i) => (
                        <div key={i} className={`text-[10px] px-1 py-0.5 rounded mb-0.5 truncate ${TYPE_COLORS[item.type].bg} ${TYPE_COLORS[item.type].text}`} title={item.title}>
                          {TYPE_COLORS[item.type].label} {item.title?.slice(0, 8)}
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* Reels Tab */}
        {tab === "reels" && (
          <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
            <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
              <h2 className="text-base font-semibold text-white">릴스/쇼츠 콘티</h2>
              <button onClick={loadContis} className="text-xs text-gray-400 border border-[#2a2a3a] px-3 py-1 rounded hover:text-white">새로고침</button>
            </div>
            <div className="p-5 space-y-4">
              {/* 요청 폼 */}
              <div className="bg-[#0f0f13] p-4 rounded-lg space-y-3">
                <p className="text-xs text-gray-500 font-semibold">콘티 생성 요청</p>
                <div className="flex gap-3 flex-wrap">
                  <input placeholder="참고 영상 URL (선택)" value={reelForm.url} onChange={e => setReelForm({...reelForm, url: e.target.value})} className="flex-1 min-w-[200px] bg-[#1a1a24] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded text-sm" />
                  <select value={reelForm.contentType} onChange={e => setReelForm({...reelForm, contentType: e.target.value})} className="bg-[#1a1a24] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded text-sm">
                    <option>알바 썰</option><option>개발 자랑</option><option>학습 공유</option><option>과거 썰</option>
                  </select>
                </div>
                <div className="flex gap-3">
                  <input placeholder="내 썰/아이디어 입력" value={reelForm.story} onChange={e => setReelForm({...reelForm, story: e.target.value})} className="flex-1 bg-[#1a1a24] border border-[#2a2a3a] text-gray-200 px-3 py-2 rounded text-sm" />
                  <button disabled={reelRequesting || !reelForm.story.trim()} onClick={async () => {
                    setReelRequesting(true);
                    try {
                      const data = await api("/api/conti-request", {
                        method: "POST",
                        body: JSON.stringify({ type: reelForm.url ? "url" : "story", url: reelForm.url, story: reelForm.story, content_type: reelForm.contentType }),
                      });
                      alert(data.message);
                      setReelForm({ url: "", story: "", contentType: "알바 썰" });
                      loadContis();
                    } catch (e) { alert((e as Error).message); }
                    finally { setReelRequesting(false); }
                  }} className="bg-purple-600 text-white px-5 py-2 rounded text-sm font-semibold hover:bg-purple-700 disabled:bg-gray-700 disabled:text-gray-500">
                    {reelRequesting ? "요청중..." : "콘티 요청"}
                  </button>
                </div>
              </div>

              {contis.length === 0 ? <p className="text-center text-gray-600 py-8">콘티가 없습니다.</p> : (
                <table className="w-full text-sm">
                  <thead><tr className="text-xs text-gray-500 border-b border-[#2a2a3a]">
                    <th className="text-left p-2">ID</th><th className="text-left p-2">날짜</th><th className="text-left p-2">제목</th>
                    <th className="text-left p-2">유형</th><th className="text-left p-2">길이</th><th className="text-left p-2">상태</th>
                  </tr></thead>
                  <tbody>{contis.reverse().map((c) => (
                    <tr key={c["ID"]} className="border-b border-[#1f1f2f] hover:bg-[#1f1f2f]">
                      <td className="p-2 text-xs text-gray-600">{c["ID"]}</td>
                      <td className="p-2">{c["날짜"]}</td>
                      <td className="p-2">{c["제목"]}</td>
                      <td className="p-2 text-xs text-gray-400">{c["유형"]}</td>
                      <td className="p-2 text-xs">{c["총길이(초)"]}초</td>
                      <td className={`p-2 text-xs font-semibold ${STATUS_COLORS[c["상태"]] || ""}`}>{c["상태"]}</td>
                    </tr>
                  ))}</tbody>
                </table>
              )}
            </div>
          </section>
        )}

        {/* Threads Tab */}
        {tab === "threads" && (
          <section className="bg-[#1a1a24] border border-[#2a2a3a] rounded-xl">
            <div className="px-5 py-4 border-b border-[#2a2a3a] flex justify-between items-center">
              <h2 className="text-base font-semibold text-white">쓰레드</h2>
              <button onClick={loadThreads} className="text-xs text-gray-400 border border-[#2a2a3a] px-3 py-1 rounded hover:text-white">새로고침</button>
            </div>
            <div className="p-5">
              {threads.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500 mb-3">블로그 초안에서 Threads 글을 자동 생성하세요</p>
                  <p className="text-xs text-gray-600">대시보드 → 블로그 미리보기 → &quot;Threads 생성&quot; 버튼</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {threads.reverse().map((t) => (
                    <div key={t["ID"]} className="bg-[#0f0f13] rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex gap-2 text-xs text-gray-500">
                          <span>{t["날짜"]}</span>
                          <span className="text-pink-400">{t["원본타입"]} → {t["원본ID"]}</span>
                          <span className={STATUS_COLORS[t["상태"]] || ""}>{t["상태"]}</span>
                        </div>
                        <button onClick={() => copyThread(t["내용"])} className="text-xs text-emerald-400 border border-emerald-800 px-2 py-1 rounded hover:bg-emerald-900">복사</button>
                      </div>
                      <p className="text-sm text-gray-300 whitespace-pre-wrap">{t["내용"]}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
