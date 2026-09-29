"use client";

import { useState } from "react";
import { Check, ChevronDown, Clock3, Minus, PencilLine, Plus, UserRound } from "lucide-react";
import type { Offering, Slot } from "@/lib/types";

type Props = {
  offerings: Offering[];
  slots: Slot[];
  onChange: (offerings: Offering[]) => void;
};

export function OfferingEditor({ offerings, slots, onChange }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function update(id: string, patch: Partial<Offering>) {
    onChange(offerings.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  const selected = offerings.filter((item) => item.enabled !== false).length;

  function addOffering() {
    const id = `custom-${Date.now()}`;
    const newOffering: Offering = {
      id,
      code: "CSE-NEW",
      title: "درس جدید",
      instructor: "نام استاد",
      preferred_semester: 5,
      groups: 1,
      capacity: 35,
      available_slot_ids: slots.slice(0, 4).map((slot) => slot.id),
      flexibility: 3,
      kind: "theory",
      enabled: true,
    };
    onChange([...offerings, newOffering]);
    setExpandedId(id);
  }

  function toggleSlot(item: Offering, slotId: string) {
    const exists = item.available_slot_ids.includes(slotId);
    const next = exists
      ? item.available_slot_ids.filter((id) => id !== slotId)
      : [...item.available_slot_ids, slotId];
    if (next.length > 0) update(item.id, { available_slot_ids: next });
  }

  return (
    <section className="panel offerings-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">مرحله ۱ از ۳</span>
          <h2>دروس قابل ارائه این ترم</h2>
          <p>درس‌ها، استاد و تعداد گروه‌ها را بررسی کنید.</p>
        </div>
        <div className="heading-actions">
          <div className="selection-count"><Check size={15} /> {selected} درس فعال</div>
          <button className="add-course-button" type="button" onClick={addOffering}><Plus size={14} /> افزودن درس</button>
        </div>
      </div>

      <div className="offering-list">
        {offerings.map((item) => {
          const enabled = item.enabled !== false;
          return (
            <article className={`offering-card ${enabled ? "selected" : ""} ${expandedId === item.id ? "expanded" : ""}`} key={item.id}>
              <div className="offering-row">
                <button
                  type="button"
                  className="select-dot"
                  aria-label={`${enabled ? "حذف" : "افزودن"} ${item.title}`}
                  onClick={() => update(item.id, { enabled: !enabled })}
                >
                  {enabled && <Check size={14} />}
                </button>
                <div className="course-main">
                  <div className="course-title-row">
                    <h3>{item.title}</h3>
                    <span className={`course-kind ${item.kind}`}>{item.kind === "skill" ? "مهارتی" : item.kind === "lab" ? "آزمایشگاه" : "نظری"}</span>
                  </div>
                  <div className="course-meta">
                    <span><UserRound size={14} />{item.instructor}</span>
                    <span><Clock3 size={14} />{item.available_slot_ids.length} زمان آزاد</span>
                    <span className="code">{item.code}</span>
                  </div>
                </div>
                <div className="group-stepper">
                  <span>تعداد گروه</span>
                  <div>
                    <button type="button" onClick={() => update(item.id, { groups: Math.max(1, item.groups - 1) })}><Minus size={14} /></button>
                    <strong>{item.groups}</strong>
                    <button type="button" onClick={() => update(item.id, { groups: Math.min(8, item.groups + 1) })}><Plus size={14} /></button>
                  </div>
                </div>
                <button className="edit-course-button" type="button" onClick={() => setExpandedId(expandedId === item.id ? null : item.id)} aria-label={`ویرایش ${item.title}`}>
                  {expandedId === item.id ? <ChevronDown size={15} /> : <PencilLine size={14} />}
                </button>
              </div>

              {expandedId === item.id && (
                <div className="offering-details">
                  <label><span>نام درس</span><input value={item.title} onChange={(event) => update(item.id, { title: event.target.value })} /></label>
                  <label><span>کد درس</span><input dir="ltr" value={item.code} onChange={(event) => update(item.id, { code: event.target.value })} /></label>
                  <label><span>نام استاد</span><input value={item.instructor} onChange={(event) => update(item.id, { instructor: event.target.value })} /></label>
                  <label><span>ظرفیت هر گروه</span><input type="number" min={5} max={300} value={item.capacity} onChange={(event) => update(item.id, { capacity: Number(event.target.value) })} /></label>
                  <label><span>ترم پیشنهادی</span><select value={item.preferred_semester} onChange={(event) => update(item.id, { preferred_semester: Number(event.target.value) })}>{[1,2,3,4,5,6,7,8].map((semester) => <option key={semester} value={semester}>ترم {semester}</option>)}</select></label>
                  <label><span>نوع درس</span><select value={item.kind} onChange={(event) => update(item.id, { kind: event.target.value as Offering["kind"] })}><option value="theory">نظری</option><option value="lab">آزمایشگاهی</option><option value="skill">مهارتی</option></select></label>
                  <fieldset className="slot-picker">
                    <legend>زمان‌های آزاد استاد</legend>
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
