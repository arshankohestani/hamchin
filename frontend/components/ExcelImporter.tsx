"use client";

import { useRef, useState } from "react";
import { FileSpreadsheet, ListPlus, RefreshCw, Upload } from "lucide-react";
import type { CourseSession, Offering, Slot } from "@/lib/types";

type Props = {
  slots: Slot[];
  onImport: (offerings: Offering[], mode: "replace" | "append") => void;
};

type Cell = string | number | boolean | Date | null;

const aliases = {
  code: ["کد درس", "کد", "course code", "code"],
  title: ["نام درس", "عنوان درس", "درس", "course", "course name"],
  instructor: ["نام استاد", "استاد", "teacher", "instructor"],
  semester: ["ترم پیشنهادی", "ترم", "semester"],
  group: ["شماره گروه", "گروه", "group"],
  capacity: ["ظرفیت", "capacity"],
  kind: ["نوع درس", "نوع", "kind"],
  sessions: ["تعداد جلسات", "جلسات", "sessions"],
  availability: ["زمان های آزاد استاد", "زمان آزاد استاد", "ساعات آزاد استاد", "زمان های آزاد", "availability"],
} as const;

function normalize(value: Cell | undefined) {
  return String(value ?? "")
    .replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)))
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/\u200c/g, " ")
    .replace(/[_\-–—،,:؛;()]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function findColumn(headers: Cell[], names: readonly string[]) {
  const normalizedNames = names.map((name) => normalize(name));
  return headers.findIndex((header) => normalizedNames.includes(normalize(header)));
}

function numberValue(value: Cell | undefined, fallback: number, min: number, max: number) {
  const parsed = Number(normalize(value));
  return Number.isFinite(parsed) ? Math.min(max, Math.max(min, Math.round(parsed))) : fallback;
}

function patternValue(value: Cell | undefined): CourseSession["week_pattern"] {
  const text = normalize(value);
  if (text.includes("فرد") || text === "odd") return "odd";
  if (text.includes("زوج") || text === "even") return "even";
  return "every";
}

function findSlots(value: Cell | undefined, slots: Slot[]) {
  const text = normalize(value);
  if (!text) return [];
  if (text === "همه" || text === "all") return slots.map((slot) => slot.id);
  const pieces = String(value).split(/[\n,،;؛|/]+/).map((piece) => normalize(piece)).filter(Boolean);
  return slots.filter((slot) => pieces.some((piece) => {
    const label = normalize(slot.label);
    const day = normalize(slot.day);
    const start = normalize(slot.start).replace(":00", "");
    const end = normalize(slot.end).replace(":00", "");
    return piece === normalize(slot.id) || piece === label || (piece.includes(day) && piece.includes(start) && piece.includes(end));
  })).map((slot) => slot.id);
}

function safeId(value: string, fallback: string) {
  const latin = normalize(value).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return latin || fallback;
}

export function ExcelImporter({ slots, onImport }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [parsed, setParsed] = useState<Offering[]>([]);
  const [fileName, setFileName] = useState("");
  const [message, setMessage] = useState("فایل xlsx با عنوان ستون‌های فارسی یا انگلیسی قابل خواندن است.");
  const [busy, setBusy] = useState(false);

  async function readFile(file: File) {
    setBusy(true);
    setParsed([]);
    setFileName(file.name);
    try {
      const { readSheet } = await import("read-excel-file/browser");
      const rows = await readSheet(file) as Cell[][];
      const headerIndex = rows.findIndex((row) => {
        const known = Object.values(aliases).flat().map(normalize);
        return row.filter((cell) => known.includes(normalize(cell))).length >= 2;
      });
      if (headerIndex < 0) throw new Error("ردیف عنوان ستون‌ها پیدا نشد.");
      const headers = rows[headerIndex];
      const columns = Object.fromEntries(
        Object.entries(aliases).map(([key, names]) => [key, findColumn(headers, names)]),
      ) as Record<keyof typeof aliases, number>;
      if (columns.code < 0 || columns.title < 0 || columns.instructor < 0) {
        throw new Error("ستون‌های «کد درس»، «نام درس» و «نام استاد» الزامی‌اند.");
      }

      const courseIds = new Map<string, string>();
      const imported: Offering[] = [];
      rows.slice(headerIndex + 1).forEach((row, rowIndex) => {
        const code = String(row[columns.code] ?? "").trim();
        const title = String(row[columns.title] ?? "").trim();
        const instructor = String(row[columns.instructor] ?? "").trim();
        if (!code && !title && !instructor) return;
        if (!code || !title || !instructor) throw new Error(`ردیف ${headerIndex + rowIndex + 2} ناقص است.`);
        const courseKey = `${normalize(code)}-${normalize(title)}`;
        if (!courseIds.has(courseKey)) courseIds.set(courseKey, safeId(code, `excel-course-${courseIds.size + 1}`));
        const courseId = courseIds.get(courseKey)!;
        const groupNumber = numberValue(row[columns.group], 1, 1, 99);
        const sessionCount = numberValue(row[columns.sessions], 1, 1, 6);
        const generalAvailability = columns.availability >= 0 ? findSlots(row[columns.availability], slots) : [];
        const sessions: CourseSession[] = [];
        const available = new Set(generalAvailability);
        for (let number = 1; number <= sessionCount; number += 1) {
          const patternColumn = headers.findIndex((header) => {
            const text = normalize(header);
            return text.includes(`جلسه ${number}`) && (text.includes("الگو") || text.includes("تکرار") || text.includes("هفته"));
          });
          const timeColumn = headers.findIndex((header) => {
            const text = normalize(header);
            return text.includes(`جلسه ${number}`) && (text.includes("زمان") || text.includes("ساعت"));
          });
          const fixedSlots = timeColumn >= 0 ? findSlots(row[timeColumn], slots) : [];
          fixedSlots.forEach((slotId) => available.add(slotId));
          sessions.push({
            meeting_number: number,
            week_pattern: patternValue(patternColumn >= 0 ? row[patternColumn] : null),
            fixed_slot_id: fixedSlots[0] ?? null,
          });
        }
        const kindText = normalize(columns.kind >= 0 ? row[columns.kind] : null);
        const kind: Offering["kind"] = kindText.includes("آزمایش") || kindText === "lab"
          ? "lab"
          : kindText.includes("مهارت") || kindText === "skill" ? "skill" : "theory";
        imported.push({
          id: `${courseId}-g${groupNumber}-excel-${rowIndex + 1}`,
          course_id: courseId,
          code,
          title,
          instructor,
          preferred_semester: numberValue(row[columns.semester], 1, 1, 8),
          group_number: groupNumber,
          weekly_sessions: sessions.length,
          week_pattern: sessions[0].week_pattern,
          sessions,
          capacity: numberValue(row[columns.capacity], 35, 5, 300),
          available_slot_ids: [...available],
          flexibility: 3,
          kind,
          enabled: true,
        });
      });
      if (!imported.length) throw new Error("هیچ ردیف درسی قابل استفاده‌ای پیدا نشد.");
      setParsed(imported);
      const missing = imported.filter((item) => item.available_slot_ids.length === 0).length;
      setMessage(`${imported.length} گروه خوانده شد${missing ? `؛ زمان آزاد ${missing} گروه باید در فرم تکمیل شود` : " و آماده ورود است"}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "خواندن فایل اکسل انجام نشد.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <section className="panel excel-import-panel">
      <div className="excel-icon"><FileSpreadsheet size={21} /></div>
      <div className="excel-copy">
        <h2>ورود اطلاعات از اکسل</h2>
        <p>{message}</p>
        <small>ستون‌های لازم: کد درس، نام درس، نام استاد. ستون‌های ترم، گروه، ظرفیت، تعداد جلسات، زمان‌های آزاد و «الگو/زمان جلسه ۱…۶» اختیاری‌اند.</small>
      </div>
      <input ref={inputRef} hidden type="file" accept=".xlsx" onChange={(event) => event.target.files?.[0] && void readFile(event.target.files[0])} />
      <button className="excel-upload" type="button" disabled={busy} onClick={() => inputRef.current?.click()}>
        {busy ? <RefreshCw className="spin" size={15} /> : <Upload size={15} />} {busy ? "در حال خواندن…" : "انتخاب فایل اکسل"}
      </button>
      {parsed.length > 0 && (
        <div className="excel-import-actions">
          <span>{fileName} · {parsed.length} گروه</span>
          <button type="button" onClick={() => onImport(parsed, "append")}><ListPlus size={14} /> افزودن به فهرست</button>
          <button type="button" onClick={() => onImport(parsed, "replace")}><RefreshCw size={14} /> جایگزینی فهرست فعلی</button>
        </div>
      )}
    </section>
  );
}
