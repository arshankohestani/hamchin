"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarCheck2, CheckCircle2, CircleAlert, MapPin, Sparkles } from "lucide-react";
import type { ScheduleResult, Slot } from "@/lib/types";

const weekLabels = { every: "هر هفته", odd: "هفته فرد", even: "هفته زوج" } as const;

type Props = {
  result: ScheduleResult;
  slots: Slot[];
  approving: boolean;
  approved: boolean;
  onApprove: () => void;
};

export function ScheduleView({ result, slots, approving, approved, onApprove }: Props) {
  const [selectedId, setSelectedId] = useState("semester-1");
  useEffect(() => setSelectedId("semester-1"), [result.revision_id]);

  const programs = result.schedule_programs?.length
    ? result.schedule_programs
    : [{ id: "overall", label: "برنامه کامل همه ترم‌ها", semester: null, assignments: result.assignments }];
  const selected = programs.find((program) => program.id === selectedId) ?? programs[0];
  const days = useMemo(() => [...new Set(slots.map((slot) => slot.day))], [slots]);
  const timeRanges = useMemo(() => {
    const unique = new Map<string, { start: string; end: string }>();
    slots.forEach((slot) => unique.set(slot.start, { start: slot.start, end: slot.end }));
    return [...unique.values()].sort((left, right) => left.start.localeCompare(right.start));
  }, [slots]);

  return (
    <section className="results-section">
      <div className="result-title-row">
        <div>
          <span className="eyebrow"><Sparkles size={14} /> خروجی موتور هوشمند</span>
          <h2>{result.name}</h2>
          <p>نسخه {result.revision_id} · ۸ برنامه ترمی و یک برنامه کامل از یک حل سراسری</p>
        </div>
        <div className="result-actions">
          <button className="secondary-button" type="button">ذخیره پیش‌نویس</button>
          <button className="approve-button" type="button" disabled={approving || approved} onClick={onApprove}>
            <CalendarCheck2 size={18} />
            {approved ? "تأیید شد" : approving ? "در حال تأیید…" : "تأیید نهایی برنامه"}
          </button>
        </div>
      </div>

      <div className="metrics-grid">
        {result.metrics.map((metric) => (
          <article className={`metric-card ${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.change}</small>
          </article>
        ))}
      </div>

      <div className="program-tabs" role="tablist" aria-label="انتخاب برنامه ترمی یا کامل">
        {programs.map((program) => (
          <button key={program.id} className={selected.id === program.id ? "active" : ""} type="button" role="tab" aria-selected={selected.id === program.id} onClick={() => setSelectedId(program.id)}>
            {program.label}<small>{program.assignments.length} جلسه</small>
          </button>
        ))}
      </div>

      <div className="schedule-layout">
        <div className="panel calendar-panel">
          <div className="panel-heading compact">
            <div><h2>{selected.label}</h2><p>همه نماها از یک برنامه مادر هستند؛ بنابراین تداخل استاد و کلاس بین ترم‌ها هم کنترل شده است.</p></div>
          </div>
          {selected.assignments.length === 0 ? (
            <div className="schedule-empty">برای این ترم هنوز درس فعالی تعریف نشده است.</div>
          ) : (
            <div className="calendar-scroll">
              <div className="calendar-grid" style={{ "--day-count": days.length } as React.CSSProperties}>
                <div className="calendar-corner">ساعت</div>
                {days.map((day) => <div className="calendar-day" key={day}>{day}</div>)}
                {timeRanges.map((range) => (
                  <div className="calendar-row" key={range.start}>
                    <div className="calendar-time">{range.start}<small>تا {range.end}</small></div>
                    {days.map((day) => {
                      const assignments = selected.assignments.filter((item) => item.slot.day === day && item.slot.start === range.start);
                      return (
                        <div className="calendar-cell" key={`${day}-${range.start}`}>
                          {assignments.map((item) => (
                            <div className={`class-chip semester-${item.semester}`} key={item.section_id}>
                              <strong>{item.course_title}</strong>
                              <span>گروه {item.group_number} · جلسه {item.meeting_number} · {item.instructor}</span>
                              <small className="week-pattern">{weekLabels[item.week_pattern]}</small>
                              <small><MapPin size={11} />{item.room ?? "کلاس تعیین نشده"}</small>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="analysis-column">
          <div className="panel insight-card">
            <div className="insight-icon"><Sparkles size={19} /></div><h3>تحلیل این نسخه</h3>
            <ul>{result.insights.map((item) => <li key={item}><CheckCircle2 size={15} />{item}</li>)}</ul>
            <p className="demand-basis">مبنای سنجش: {result.demand_basis}</p>
          </div>
          {result.unresolved.length > 0 && <div className="panel warning-card"><CircleAlert size={19} /><div><h3>قابل بهبود</h3>{result.unresolved.map((item) => <p key={item}>{item}</p>)}</div></div>}
          <div className="panel score-ring-card">
            <div className="score-ring" style={{ "--score": `${result.score * 3.6}deg` } as React.CSSProperties}><div><strong>{result.score}</strong><span>از ۱۰۰</span></div></div>
            <div><h3>امتیاز کیفیت</h3><p>این امتیاز با تداخل‌ها و آزادی انتخاب محاسبه شده است.</p></div>
          </div>
        </aside>
      </div>
    </section>
  );
}
