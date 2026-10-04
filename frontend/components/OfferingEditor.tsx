"use client";

import { useState } from "react";
import {
  Check,
  ChevronDown,
  Clock3,
  CopyPlus,
  Minus,
  PencilLine,
  Plus,
  Trash2,
  UserRound,
} from "lucide-react";
import type { CourseSession, Offering, Slot } from "@/lib/types";

type Props = {
  offerings: Offering[];
  slots: Slot[];
  onChange: (offerings: Offering[]) => void;
};

const weekLabels: Record<CourseSession["week_pattern"], string> = {
  every: "هر هفته",
  odd: "هفته‌های فرد",
  even: "هفته‌های زوج",
};

export function OfferingEditor({ offerings, slots, onChange }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function update(id: string, patch: Partial<Offering>) {
    onChange(offerings.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  function updateCourse(item: Offering, patch: Partial<Offering>) {
    onChange(
      offerings.map((candidate) =>
        candidate.course_id === item.course_id ? { ...candidate, ...patch } : candidate,
      ),
    );
  }

  function setSessions(item: Offering, sessions: CourseSession[]) {
    const normalized = sessions.map((session, index) => ({
      ...session,
      meeting_number: index + 1,
    }));
    update(item.id, {
      sessions: normalized,
      weekly_sessions: normalized.length,
      week_pattern: normalized[0]?.week_pattern ?? "every",
    });
  }

  const activeOfferings = offerings.filter((item) => item.enabled !== false);
  const activeCourses = new Set(activeOfferings.map((item) => item.course_id)).size;

  function addOffering() {
    const timestamp = Date.now();
    const courseId = `custom-${timestamp}`;
    const newOffering: Offering = {
      id: `${courseId}-g1`,
      course_id: courseId,
      code: "CSE-NEW",
      title: "درس جدید",
      instructor: "نام استاد",
      preferred_semester: 5,
      group_number: 1,
      weekly_sessions: 1,
      week_pattern: "every",
      sessions: [{ meeting_number: 1, week_pattern: "every", fixed_slot_id: null }],
      capacity: 35,
      available_slot_ids: slots.slice(0, 4).map((slot) => slot.id),
      flexibility: 3,
      kind: "theory",
      enabled: true,
    };
    onChange([...offerings, newOffering]);
    setExpandedId(newOffering.id);
  }

  function addExtraGroup(source: Offering) {
    const sameCourse = offerings.filter((item) => item.course_id === source.course_id);
    const nextGroup = Math.max(...sameCourse.map((item) => item.group_number), 0) + 1;
    const extra: Offering = {
      ...source,
      id: `${source.course_id}-g${nextGroup}-${Date.now()}`,
      group_number: nextGroup,
      sessions: source.sessions.map((session) => ({ ...session, fixed_slot_id: null })),
      enabled: true,
    };
    onChange([...offerings, extra]);
    setExpandedId(extra.id);
  }

  function removeGroup(item: Offering) {
    const sameCourse = offerings.filter((candidate) => candidate.course_id === item.course_id);
    if (sameCourse.length <= 1) return;
    onChange(offerings.filter((candidate) => candidate.id !== item.id));
    if (expandedId === item.id) setExpandedId(null);
  }

  function toggleSlot(item: Offering, slotId: string) {
    const exists = item.available_slot_ids.includes(slotId);
    const next = exists
      ? item.available_slot_ids.filter((id) => id !== slotId)
      : [...item.available_slot_ids, slotId];
    if (next.length > 0) {
      update(item.id, {
        available_slot_ids: next,
        sessions: item.sessions.map((session) =>
          session.fixed_slot_id === slotId ? { ...session, fixed_slot_id: null } : session,
        ),
      });
    }
  }

  return (
    <section className="panel offerings-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">مرحله ۱ از ۳</span>
          <h2>گروه‌های قابل ارائه این ترم</h2>
          <p>هر کارت یک گروه مستقل است؛ استاد، جلسات و هفتهٔ برگزاری را مشخص کنید.</p>
        </div>
        <div className="heading-actions">
          <div className="selection-count"><Check size={15} /> {activeCourses} درس · {activeOfferings.length} گروه</div>
          <button className="add-course-button" type="button" onClick={addOffering}><Plus size={14} /> افزودن درس</button>
        </div>
      </div>

      <div className="offering-list">
        {offerings.map((item) => {
          const enabled = item.enabled !== false;
          const sameCourseCount = offerings.filter((candidate) => candidate.course_id === item.course_id).length;
          const patterns = new Set(item.sessions.map((session) => session.week_pattern));
          const patternSummary = patterns.size === 1
            ? weekLabels[item.sessions[0].week_pattern]
            : "الگوی ترکیبی جلسات";
          return (
            <article className={`offering-card ${enabled ? "selected" : ""} ${expandedId === item.id ? "expanded" : ""}`} key={item.id}>
              <div className="offering-row">
                <button
                  type="button"
                  className="select-dot"
                  aria-label={`${enabled ? "غیرفعال‌کردن" : "فعال‌کردن"} ${item.title}`}
                  onClick={() => update(item.id, { enabled: !enabled })}
                >
                  {enabled && <Check size={14} />}
                </button>
                <div className="course-main">
                  <div className="course-title-row">
                    <h3>{item.title}</h3>
                    <span className="group-badge">گروه {item.group_number}</span>
                    <span className={`course-kind ${item.kind}`}>{item.kind === "skill" ? "مهارتی" : item.kind === "lab" ? "آزمایشگاهی" : "نظری"}</span>
                  </div>
                  <div className="course-meta">
                    <span><UserRound size={14} />{item.instructor}</span>
                    <span><Clock3 size={14} />{item.available_slot_ids.length} زمان آزاد</span>
                    <span>{patternSummary}</span>
                    <span className="code">{item.code}</span>
                  </div>
                </div>
                <div className="group-stepper">
                  <span>تعداد جلسه</span>
                  <div>
                    <button type="button" onClick={() => setSessions(item, item.sessions.slice(0, Math.max(1, item.sessions.length - 1)))}><Minus size={14} /></button>
                    <strong>{item.sessions.length}</strong>
                    <button type="button" onClick={() => item.sessions.length < 6 && setSessions(item, [...item.sessions, { meeting_number: item.sessions.length + 1, week_pattern: "every", fixed_slot_id: null }])}><Plus size={14} /></button>
                  </div>
                </div>
                <button className="edit-course-button" type="button" onClick={() => addExtraGroup(item)} aria-label={`افزودن گروه مازاد برای ${item.title}`} title="افزودن گروه مازاد">
                  <CopyPlus size={14} />
                </button>
                <button className="edit-course-button" type="button" onClick={() => setExpandedId(expandedId === item.id ? null : item.id)} aria-label={`ویرایش ${item.title}`}>
                  {expandedId === item.id ? <ChevronDown size={15} /> : <PencilLine size={14} />}
                </button>
              </div>

              {expandedId === item.id && (
                <div className="offering-details">
                  <label><span>نام درس</span><input value={item.title} onChange={(event) => updateCourse(item, { title: event.target.value })} /></label>
                  <label><span>کد درس</span><input dir="ltr" value={item.code} onChange={(event) => updateCourse(item, { code: event.target.value })} /></label>
                  <label><span>شماره گروه</span><input type="number" min={1} max={99} value={item.group_number} onChange={(event) => update(item.id, { group_number: Number(event.target.value) })} /></label>
                  <label><span>نام استاد این گروه</span><input value={item.instructor} onChange={(event) => update(item.id, { instructor: event.target.value })} /></label>
                  <label><span>ظرفیت این گروه</span><input type="number" min={5} max={300} value={item.capacity} onChange={(event) => update(item.id, { capacity: Number(event.target.value) })} /></label>
                  <label><span>ترم پیشنهادی</span><select value={item.preferred_semester} onChange={(event) => updateCourse(item, { preferred_semester: Number(event.target.value) })}>{[1,2,3,4,5,6,7,8].map((semester) => <option key={semester} value={semester}>ترم {semester}</option>)}</select></label>
                  <label><span>نوع درس</span><select value={item.kind} onChange={(event) => updateCourse(item, { kind: event.target.value as Offering["kind"] })}><option value="theory">نظری</option><option value="lab">آزمایشگاهی</option><option value="skill">مهارتی</option></select></label>
                  <div className="session-config">
                    <div className="session-config-heading">
                      <strong>تنظیم جداگانه جلسه‌ها</strong>
                      <span>برای هر جلسه، نوع هفته و روز و ساعت را مستقل انتخاب کنید.</span>
                    </div>
                    {item.sessions.map((session, sessionIndex) => (
                      <div className="session-row" key={session.meeting_number}>
                        <span className="session-number">جلسه {session.meeting_number}</span>
                        <label>
                          <span>نحوه تکرار</span>
                          <select
                            value={session.week_pattern}
                            onChange={(event) => setSessions(item, item.sessions.map((candidate, index) =>
                              index === sessionIndex
                                ? { ...candidate, week_pattern: event.target.value as CourseSession["week_pattern"] }
                                : candidate,
                            ))}
                          >
                            <option value="every">هر هفته</option>
                            <option value="odd">فقط هفته‌های فرد</option>
                            <option value="even">فقط هفته‌های زوج</option>
                          </select>
                        </label>
                        <label>
                          <span>روز و ساعت این جلسه</span>
                          <select
                            value={session.fixed_slot_id ?? ""}
                            onChange={(event) => setSessions(item, item.sessions.map((candidate, index) =>
                              index === sessionIndex
                                ? { ...candidate, fixed_slot_id: event.target.value || null }
                                : candidate,
                            ))}
                          >
                            <option value="">انتخاب هوشمند از ساعت‌های آزاد استاد</option>
                            {slots
                              .filter((slot) => item.available_slot_ids.includes(slot.id))
                              .map((slot) => <option key={slot.id} value={slot.id}>{slot.label}</option>)}
                          </select>
                        </label>
                      </div>
                    ))}
                  </div>
                  <div className="group-tools">
                    <button type="button" onClick={() => addExtraGroup(item)}><CopyPlus size={14} /> افزودن گروه مازاد با امکان استاد متفاوت</button>
                    <button type="button" className="danger" disabled={sameCourseCount <= 1} onClick={() => removeGroup(item)}><Trash2 size={14} /> حذف این گروه</button>
                  </div>
                  <fieldset className="slot-picker">
                    <legend>زمان‌های آزاد استاد همین گروه</legend>
                    {slots.map((slot) => (
                      <button className={item.available_slot_ids.includes(slot.id) ? "active" : ""} type="button" key={slot.id} onClick={() => toggleSlot(item, slot.id)}>
                        {item.available_slot_ids.includes(slot.id) && <Check size={11} />}{slot.label}
                      </button>
                    ))}
                  </fieldset>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
