"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Plus, Trash2, UsersRound } from "lucide-react";
import type { DemandGroup, Offering } from "@/lib/types";

type Props = {
  groups: DemandGroup[];
  offerings: Offering[];
  onChange: (groups: DemandGroup[]) => void;
};

export function DemandEditor({ groups, offerings, onChange }: Props) {
  const [expanded, setExpanded] = useState(false);

  function update(id: string, patch: Partial<DemandGroup>) {
    onChange(groups.map((group) => (group.id === id ? { ...group, ...patch } : group)));
  }

  function toggleCourse(group: DemandGroup, courseId: string) {
    const selected = group.course_ids.includes(courseId);
    const next = selected
      ? group.course_ids.filter((id) => id !== courseId)
      : [...group.course_ids, courseId];
    if (next.length >= 2) update(group.id, { course_ids: next });
  }

  function addGroup() {
    const initialCourses = offerings.filter((item) => item.enabled !== false).slice(0, 2).map((item) => item.id);
    if (initialCourses.length < 2) return;
    onChange([
      ...groups,
      {
        id: `demand-${Date.now()}`,
        label: "سناریوی جدید دانشجویان",
        student_count: 10,
        course_ids: initialCourses,
        weight: 5,
        source: "requested",
      },
    ]);
    setExpanded(true);
  }

  const totalStudents = groups.reduce((sum, group) => sum + group.student_count, 0);

  return (
    <section className="panel demand-panel">
      <div className="room-panel-head">
        <div className="room-title">
          <span className="room-icon demand"><UsersRound size={17} /></span>
          <div><h2>سناریوهای تقاضای دانشجو</h2><p>{groups.length} سناریو · مجموع وزنی {totalStudents} دانشجو</p></div>
        </div>
        <div className="room-actions">
          <button type="button" onClick={addGroup}><Plus size={14} /> سناریو</button>
          <button type="button" onClick={() => setExpanded(!expanded)}>{expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />} مدیریت</button>
        </div>
      </div>
      {expanded && (
        <div className="demand-list">
          {groups.map((group) => (
            <article className="demand-row" key={group.id}>
              <div className="demand-fields">
                <input aria-label="عنوان سناریو" value={group.label} onChange={(event) => update(group.id, { label: event.target.value })} />
                <label><span>تعداد</span><input type="number" min={1} max={10000} value={group.student_count} onChange={(event) => update(group.id, { student_count: Number(event.target.value) })} /></label>
                <label><span>اهمیت</span><input type="number" min={1} max={10} value={group.weight} onChange={(event) => update(group.id, { weight: Number(event.target.value) })} /></label>
                <button className="remove-room" type="button" onClick={() => onChange(groups.filter((item) => item.id !== group.id))} aria-label={`حذف ${group.label}`}><Trash2 size={14} /></button>
              </div>
              <div className="demand-courses">
                {offerings.filter((item) => item.enabled !== false).map((offering) => (
                  <button type="button" className={group.course_ids.includes(offering.id) ? "active" : ""} key={offering.id} onClick={() => toggleCourse(group, offering.id)}>{offering.title}</button>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

