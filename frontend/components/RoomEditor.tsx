"use client";

import { useState } from "react";
import { Building2, ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import type { Room } from "@/lib/types";

type Props = {
  rooms: Room[];
  onChange: (rooms: Room[]) => void;
};

export function RoomEditor({ rooms, onChange }: Props) {
  const [expanded, setExpanded] = useState(false);

  function update(id: string, patch: Partial<Room>) {
    onChange(rooms.map((room) => (room.id === id ? { ...room, ...patch } : room)));
  }

  function addRoom() {
    onChange([
      ...rooms,
      {
        id: `room-${Date.now()}`,
        name: "کلاس جدید",
        capacity: 35,
        kind: "classroom",
      },
    ]);
    setExpanded(true);
  }

  return (
    <section className="panel room-panel">
      <div className="room-panel-head">
        <div className="room-title">
          <span className="room-icon"><Building2 size={17} /></span>
          <div><h2>کلاس‌ها و آزمایشگاه‌ها</h2><p>{rooms.length} فضا برای تخصیص هوشمند</p></div>
        </div>
        <div className="room-actions">
          <button type="button" onClick={addRoom}><Plus size={14} /> افزودن</button>
          <button type="button" onClick={() => setExpanded(!expanded)}>{expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />} مدیریت</button>
        </div>
      </div>
      {expanded && (
        <div className="room-list">
          {rooms.map((room) => (
            <div className="room-row" key={room.id}>
              <input aria-label="نام کلاس" value={room.name} onChange={(event) => update(room.id, { name: event.target.value })} />
              <label><span>ظرفیت</span><input type="number" min={5} max={1000} value={room.capacity} onChange={(event) => update(room.id, { capacity: Number(event.target.value) })} /></label>
              <select aria-label="نوع فضا" value={room.kind} onChange={(event) => update(room.id, { kind: event.target.value as Room["kind"] })}>
                <option value="classroom">کلاس نظری</option>
                <option value="lab">آزمایشگاه</option>
              </select>
              <button className="remove-room" type="button" disabled={rooms.length === 1} onClick={() => onChange(rooms.filter((item) => item.id !== room.id))} aria-label={`حذف ${room.name}`}><Trash2 size={14} /></button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

