"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Plus, ShieldCheck, Trash2 } from "lucide-react";
import type { ConflictGroup, Offering } from "@/lib/types";

type Props = {
  groups: ConflictGroup[];
  offerings: Offering[];
  onChange: (groups: ConflictGroup[]) => void;
};

export function ConflictGroupEditor({ groups, offerings, onChange }: Props) {
  const [expanded, setExpanded] = useState(true);
  const courses = useMemo(() => {
    const unique = new Map<string, Offering>();
    offerings
      .filter((item) => item.enabled !== false)
      .forEach((item) => {
        if (!unique.has(item.course_id)) unique.set(item.course_id, item);
      });
    return [...unique.values()];
  }, [offerings]);

  function update(id: string, patch: Partial<ConflictGroup>) {
    onChange(groups.map((group) => (group.id === id ? { ...group, ...patch } : group)));
  }

  function toggleCourse(group: ConflictGroup, courseId: string) {
    const selected = group.course_ids.includes(courseId);
    const next = selected
      ? group.course_ids.filter((id) => id !== courseId)
      : [...group.course_ids, courseId];
    if (next.length >= 2) update(group.id, { course_ids: next });
  }

  function addGroup() {
    const initialCourses = courses.slice(0, 2).map((item) => item.course_id);
    if (initialCourses.length < 2) return;
    onChange([
      ...groups,
      {
        id: `conflict-${Date.now()}`,
        label: "دسته بدون تداخل جدید",
        entry_year: "ورودی ۱۴۰۳",
        course_ids: initialCourses,
      },
    ]);
    setExpanded(true);
  }

  return (
    <section className="panel conflict-panel">
      <div className="room-panel-head">
        <div className="room-title">
          <span className="room-icon conflict"><ShieldCheck size={17} /></span>
          <div><h2>دسته‌های منع تداخل قطعی</h2><p>دروس یک ورودی یا سبد بین‌ترمی را در یک دسته بگذارید.</p></div>
        </div>
        <div className="room-actions">
          <button type="button" onClick={addGroup}><Plus size={14} /> دسته جدید</button>
          <button type="button" onClick={() => setExpanded(!expanded)}>{expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />} مدیریت</button>
        </div>
      </div>
      {expanded && (
        <div className="demand-list">
          <p className="conflict-help">حل‌کننده برای تمام درس‌های هر دسته، یک مسیر کامل و قابل اخذ بدون تداخل پیدا می‌کند؛ حتی اگر درس‌ها متعلق به ترم‌های مختلف باشند.</p>
          {groups.map((group) => (
            <article className="demand-row" key={group.id}>
              <div className="conflict-fields">
                <input aria-label="عنوان دسته" value={group.label} onChange={(event) => update(group.id, { label: event.target.value })} />
                <input aria-label="سال ورودی" value={group.entry_year} onChange={(event) => update(group.id, { entry_year: event.target.value })} placeholder="مثلاً ورودی ۱۴۰۳" />
                <button className="remove-room" type="button" onClick={() => onChange(groups.filter((item) => item.id !== group.id))} aria-label={`حذف ${group.label}`}><Trash2 size={14} /></button>
              </div>
              <div className="demand-courses">
                {courses.map((course) => (
                  <button type="button" className={group.course_ids.includes(course.course_id) ? "active" : ""} key={course.course_id} onClick={() => toggleCourse(group, course.course_id)}>
                    {course.title} <small>ترم {course.preferred_semester}</small>
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
