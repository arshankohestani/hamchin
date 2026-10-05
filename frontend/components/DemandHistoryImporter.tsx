"use client";

import { useRef, useState } from "react";
import { DatabaseZap, Upload } from "lucide-react";
import { saveDemandHistory } from "@/lib/api";
import type { Offering } from "@/lib/types";

type Props = { offerings: Offering[]; onSaved: () => void };
type Cell = string | number | boolean | Date | null;

function text(value: Cell | undefined) {
  return String(value ?? "").replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit))).replace(/\u200c/g, " ").trim().toLowerCase();
}

export function DemandHistoryImporter({ offerings, onSaved }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState("اکسل سابقه انتخاب واحد را برای آموزش CatBoost وارد کنید.");
  const [busy, setBusy] = useState(false);

  async function importFile(file: File) {
    setBusy(true);
    try {
      const { readSheet } = await import("read-excel-file/browser");
      const rows = await readSheet(file) as Cell[][];
      const headerIndex = rows.findIndex((row) => row.some((cell) => ["نیمسال", "نیم سال", "ترم", "academic term"].includes(text(cell))));
      if (headerIndex < 0) throw new Error("ردیف عنوان‌ها پیدا نشد.");
      const headers = rows[headerIndex].map(text);
      const column = (names: string[]) => headers.findIndex((header) => names.includes(header));
      const termColumn = column(["نیمسال", "نیم سال", "ترم", "academic term"]);
      const codeColumn = column(["کد درس", "کد", "course code"]);
      const enrolledColumn = column(["تعداد دانشجو", "تعداد ثبت نام", "ثبت نام", "تقاضا", "enrolled"]);
      const capacityColumn = column(["ظرفیت", "capacity"]);
      if ([termColumn, codeColumn, enrolledColumn].some((index) => index < 0)) throw new Error("ستون‌های نیمسال، کد درس و تعداد دانشجو الزامی‌اند.");
      const courseByCode = new Map(offerings.map((item) => [text(item.code), item.course_id]));
      const records = rows.slice(headerIndex + 1).flatMap((row) => {
        const courseId = courseByCode.get(text(row[codeColumn]));
        const academicTerm = String(row[termColumn] ?? "").trim();
        const enrolledCount = Number(text(row[enrolledColumn]));
        if (!courseId || !academicTerm || !Number.isFinite(enrolledCount)) return [];
        const capacity = capacityColumn >= 0 ? Number(text(row[capacityColumn])) : 0;
        return [{ academic_term: academicTerm, course_id: courseId, enrolled_count: Math.max(0, Math.round(enrolledCount)), capacity: Number.isFinite(capacity) ? Math.max(0, Math.round(capacity)) : 0 }];
      });
      if (!records.length) throw new Error("هیچ ردیفی با کد درس شناخته‌شده پیدا نشد.");
      const result = await saveDemandHistory(records);
      setMessage(`${result.saved} سابقه با موفقیت ذخیره شد و برای آموزش بعدی آماده است.`);
      onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ورود سابقه انجام نشد.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <section className="panel demand-history-panel">
      <span><DatabaseZap size={18} /></span>
      <div><h2>داده تاریخی برای پیش‌بینی تقاضا</h2><p>{message}</p><small>ستون‌ها: نیمسال، کد درس، تعداد دانشجو و ظرفیت اختیاری</small></div>
      <input ref={inputRef} hidden type="file" accept=".xlsx" onChange={(event) => event.target.files?.[0] && void importFile(event.target.files[0])} />
      <button type="button" disabled={busy} onClick={() => inputRef.current?.click()}><Upload size={14} />{busy ? "در حال ذخیره…" : "ورود اکسل سابقه"}</button>
    </section>
  );
}
