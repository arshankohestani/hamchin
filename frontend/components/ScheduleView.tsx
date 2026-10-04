"use client";

import { CalendarCheck2, CheckCircle2, CircleAlert, MapPin, Sparkles } from "lucide-react";
import type { ScheduleResult } from "@/lib/types";

const days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه"];
const times = ["08:00", "10:00", "14:00"];
const weekLabels = { every: "هر هفته", odd: "هفته فرد", even: "هفته زوج" } as const;

type Props = {
  result: ScheduleResult;
  approving: boolean;
  approved: boolean;
  onApprove: () => void;
};

export function ScheduleView({ result, approving, approved, onApprove }: Props) {
  return (
    <section className="results-section">
      <div className="result-title-row">
        <div>
          <span className="eyebrow"><Sparkles size={14} /> خروجی موتور هوشمند</span>
          <h2>{result.name}</h2>
          <p>نسخه {result.revision_id} · آماده بررسی مدیرگروه</p>
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
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.change}</small>
          </article>
        ))}
      </div>

      <div className="schedule-layout">
        <div className="panel calendar-panel">
          <div className="panel-heading compact">
            <div><h2>برنامه هفتگی پیشنهادی</h2><p>هر رنگ نماینده یک نیم‌سال پیشنهادی است.</p></div>
          </div>
          <div className="calendar-scroll">
            <div className="calendar-grid">
              <div className="calendar-corner">ساعت</div>
              {days.map((day) => <div className="calendar-day" key={day}>{day}</div>)}
              {times.map((time) => (
                <div className="calendar-row" key={time}>
                  <div className="calendar-time">{time}<small>تا {time === "14:00" ? "16:00" : time === "10:00" ? "12:00" : "10:00"}</small></div>
                  {days.map((day) => {
                    const assignments = result.assignments.filter((item) => item.slot.day === day && item.slot.start === time);
                    return (
                      <div className="calendar-cell" key={`${day}-${time}`}>
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
        </div>

        <aside className="analysis-column">
          <div className="panel insight-card">
            <div className="insight-icon"><Sparkles size={19} /></div>
            <h3>تحلیل این نسخه</h3>
            <ul>{result.insights.map((item) => <li key={item}><CheckCircle2 size={15} />{item}</li>)}</ul>
            <p className="demand-basis">مبنای سنجش: {result.demand_basis}</p>
          </div>
          {result.unresolved.length > 0 && (
            <div className="panel warning-card">
              <CircleAlert size={19} />
              <div><h3>قابل بهبود</h3>{result.unresolved.map((item) => <p key={item}>{item}</p>)}</div>
            </div>
          )}
          <div className="panel score-ring-card">
            <div className="score-ring" style={{ "--score": `${result.score * 3.6}deg` } as React.CSSProperties}>
              <div><strong>{result.score}</strong><span>از ۱۰۰</span></div>
            </div>
            <div><h3>امتیاز کیفیت</h3><p>این امتیاز با تداخل‌ها و آزادی انتخاب محاسبه شده است.</p></div>
          </div>
        </aside>
      </div>
    </section>
  );
}

