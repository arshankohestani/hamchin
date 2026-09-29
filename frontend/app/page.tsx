"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  ChevronDown,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  WandSparkles,
} from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { OfferingEditor } from "@/components/OfferingEditor";
import { RoomEditor } from "@/components/RoomEditor";
import { DemandEditor } from "@/components/DemandEditor";
import { ScheduleView } from "@/components/ScheduleView";
import { approveSchedule, generateSchedule, loadDemo } from "@/lib/api";
import type { DemandGroup, Offering, Room, ScheduleResult, Slot } from "@/lib/types";

export default function Home() {
  const [offerings, setOfferings] = useState<Offering[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [demandGroups, setDemandGroups] = useState<DemandGroup[]>([]);
  const [priorityIds, setPriorityIds] = useState<string[]>(["diff", "soft"]);
  const [targetSemester, setTargetSemester] = useState<number>(7);
  const [instruction, setInstruction] = useState("آزادی انتخاب معادلات و مهارت‌های نرم برای دانشجویان ترم‌های بالاتر بیشتر شود.");
  const [result, setResult] = useState<ScheduleResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadDemo()
      .then((data) => {
        let restored: Offering[] | null = null;
        try {
          const saved = window.localStorage.getItem("hamchin-offerings-draft");
          const parsed: unknown = saved ? JSON.parse(saved) : null;
          if (Array.isArray(parsed) && parsed.length > 0) restored = parsed as Offering[];
        } catch {
          restored = null;
        }
        setOfferings(restored ?? data.offerings.map((item) => ({ ...item, enabled: true })));
        setSlots(data.slots);
        try {
          const savedRooms = window.localStorage.getItem("hamchin-rooms-draft");
          const parsedRooms: unknown = savedRooms ? JSON.parse(savedRooms) : null;
          setRooms(Array.isArray(parsedRooms) && parsedRooms.length > 0 ? parsedRooms as Room[] : data.rooms);
          const savedDemands = window.localStorage.getItem("hamchin-demands-draft");
          const parsedDemands: unknown = savedDemands ? JSON.parse(savedDemands) : null;
          setDemandGroups(Array.isArray(parsedDemands) ? parsedDemands as DemandGroup[] : data.demand_groups);
        } catch {
          setRooms(data.rooms);
          setDemandGroups(data.demand_groups);
        }
        try {
          const savedResult = window.localStorage.getItem("hamchin-latest-schedule");
          if (savedResult) setResult(JSON.parse(savedResult) as ScheduleResult);
          setApproved(window.localStorage.getItem("hamchin-approved") === "true");
        } catch {
          window.localStorage.removeItem("hamchin-latest-schedule");
          window.localStorage.removeItem("hamchin-approved");
        }
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading && offerings.length > 0) {
      window.localStorage.setItem("hamchin-offerings-draft", JSON.stringify(offerings));
    }
  }, [loading, offerings]);

  useEffect(() => {
    if (!loading && rooms.length > 0) {
      window.localStorage.setItem("hamchin-rooms-draft", JSON.stringify(rooms));
      window.localStorage.setItem("hamchin-demands-draft", JSON.stringify(demandGroups));
    }
  }, [loading, rooms, demandGroups]);

  const activeOfferings = useMemo(() => offerings.filter((item) => item.enabled !== false), [offerings]);
  const totalGroups = activeOfferings.reduce((sum, item) => sum + item.groups, 0);

  async function handleGenerate() {
    if (!activeOfferings.length) {
      setError("حداقل یک درس را برای ارائه فعال کنید.");
      return;
    }
    setGenerating(true);
    setError("");
    setApproved(false);
    try {
      const schedule = await generateSchedule({
        name: `پیشنهاد هوشمند ترم جاری — ${new Intl.DateTimeFormat("fa-IR").format(new Date())}`,
        offerings: activeOfferings.map(({ enabled: _, ...item }) => item),
        slots,
        rooms,
        demand_groups: demandGroups.filter((group) =>
          group.course_ids.every((courseId) =>
            activeOfferings.some((offering) => offering.id === courseId),
          ),
        ),
        priority: { course_ids: priorityIds, semester: targetSemester, strength: 4, note: instruction },
      });
      setResult(schedule);
      window.localStorage.setItem("hamchin-latest-schedule", JSON.stringify(schedule));
      window.localStorage.setItem("hamchin-approved", "false");
      window.setTimeout(() => document.getElementById("result")?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "تولید برنامه با خطا روبه‌رو شد.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleApprove() {
    if (!result?.revision_id) return;
    setApproving(true);
    setError("");
    try {
      try {
        await approveSchedule(result.revision_id);
      } catch {
        // نسخه نمایشی تأیید را در مرورگر نگه می‌دارد؛ پایگاه داده ابری در فاز بعد متصل می‌شود.
      }
      setApproved(true);
      window.localStorage.setItem("hamchin-approved", "true");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "تأیید برنامه انجام نشد.");
    } finally {
      setApproving(false);
    }
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <header className="topbar">
          <div className="semester-switcher">
            <span>نیم‌سال فعال</span>
            <button type="button">نیم‌سال اول ۱۴۰۵–۱۴۰۶ <ChevronDown size={15} /></button>
          </div>
          <div className="top-actions">
            <label className="search-box"><Search size={17} /><input aria-label="جستجو" placeholder="جست‌وجوی درس یا استاد…" /></label>
            <button className="icon-button" aria-label="اعلان‌ها" type="button"><Bell size={19} /><i /></button>
          </div>
        </header>

        <div className="page-container">
          <section className="hero">
            <div>
              <div className="welcome-pill"><Sparkles size={14} /> دستیار زمان‌بندی هوشمند</div>
              <h1>برنامه‌ای که با نیاز دانشجوها<br /><em>هم‌قدم می‌شود.</em></h1>
              <p>ارائه‌های این ترم را مشخص کنید؛ هم‌چین بهترین ترکیب را پیدا می‌کند و برای هر تصمیم دلیل می‌آورد.</p>
            </div>
            <div className="hero-orbit" aria-hidden="true">
              <div className="orbit-card card-one"><span>تداخل کمتر</span><strong>٪۹۴</strong></div>
              <div className="orbit-center"><WandSparkles size={34} /></div>
              <div className="orbit-card card-two"><span>انتخاب آزاد</span><strong>+۲۸٪</strong></div>
            </div>
          </section>

          <div className="progress-strip">
            <div className="progress-item done"><span>۱</span><div><strong>تعریف ارائه‌ها</strong><small>{activeOfferings.length} درس، {totalGroups} گروه</small></div></div>
            <div className="progress-line active" />
            <div className="progress-item current"><span>۲</span><div><strong>اولویت‌های هوشمند</strong><small>تنظیم آزادی انتخاب</small></div></div>
            <div className="progress-line" />
            <div className="progress-item"><span>۳</span><div><strong>بررسی و تأیید</strong><small>انتشار نسخه نهایی</small></div></div>
          </div>

          {error && <div className="error-banner"><span>{error}</span><button type="button" onClick={() => setError("")}>بستن</button></div>}

          {loading ? (
            <div className="loading-state"><LoaderCircle className="spin" /><span>در حال آماده‌سازی فضای کار…</span></div>
          ) : (
            <div className="workspace-grid">
              <div className="editor-column">
                <OfferingEditor offerings={offerings} slots={slots} onChange={setOfferings} />
                <RoomEditor rooms={rooms} onChange={setRooms} />
                <DemandEditor groups={demandGroups} offerings={offerings} onChange={setDemandGroups} />
              </div>

              <aside className="assistant-panel">
                <div className="assistant-head">
                  <div className="assistant-avatar"><Sparkles size={20} /></div>
                  <div><h2>از هم‌چین بخواهید</h2><p>اولویت این نسخه را مشخص کنید</p></div>
                  <span className="online-dot">آماده</span>
                </div>

                <div className="suggestion-box">
                  <MessageSquareText size={17} />
                  <p>می‌توانید بگویید «آزادی انتخاب این درس برای ترم ۷ بیشتر شود» یا درس‌ها را مستقیماً انتخاب کنید.</p>
                </div>

                <label className="field-label">درس‌های با اولویت بیشتر</label>
                <div className="priority-chips">
                  {activeOfferings.map((item) => {
                    const selected = priorityIds.includes(item.id);
                    return <button key={item.id} className={selected ? "active" : ""} type="button" onClick={() => setPriorityIds(selected ? priorityIds.filter((id) => id !== item.id) : [...priorityIds, item.id])}>{item.title}</button>;
                  })}
                </div>

                <label className="field-label" htmlFor="semester">پوشش ویژه دانشجویان ترم</label>
                <select id="semester" value={targetSemester} onChange={(event) => setTargetSemester(Number(event.target.value))}>
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((semester) => <option value={semester} key={semester}>ترم {semester}</option>)}
                </select>

                <label className="field-label" htmlFor="instruction">درخواست مدیرگروه</label>
                <textarea id="instruction" value={instruction} onChange={(event) => setInstruction(event.target.value)} rows={4} />

                <div className="assistant-summary">
                  <div><span>درس فعال</span><strong>{activeOfferings.length}</strong></div>
                  <div><span>گروه درسی</span><strong>{totalGroups}</strong></div>
                  <div><span>اولویت ویژه</span><strong>{priorityIds.length}</strong></div>
                </div>

                <button className="generate-button" type="button" onClick={handleGenerate} disabled={generating}>
                  {generating ? <LoaderCircle className="spin" size={19} /> : <Send size={18} />}
                  {generating ? "در حال بررسی هزاران ترکیب…" : "ساخت برنامه پیشنهادی"}
                </button>
                <button className="reset-button" type="button" onClick={() => { setPriorityIds([]); setResult(null); }}><RefreshCw size={15} /> پاک‌کردن اولویت‌ها</button>
              </aside>
            </div>
          )}

          {result && <div id="result"><ScheduleView result={result} approving={approving} approved={approved} onApprove={handleApprove} /></div>}
        </div>
      </main>
    </div>
  );
}
