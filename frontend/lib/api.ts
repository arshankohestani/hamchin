import type { ConflictGroup, DemandGroup, DemoData, Offering, Room, ScheduleResult, Slot } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item?.msg).filter(Boolean).join("، ")
        : "ارتباط با سرور ناموفق بود.";
    throw new Error(message || "ارتباط با سرور ناموفق بود.");
  }
  return response.json() as Promise<T>;
}

export function loadDemo(): Promise<DemoData> {
  return request<DemoData>("/api/demo");
}

export function generateSchedule(input: {
  name: string;
  offerings: Offering[];
  slots: Slot[];
  rooms: Room[];
  demand_groups: DemandGroup[];
  conflict_groups: ConflictGroup[];
  priority: { course_ids: string[]; semester: number | null; strength: number; note: string };
}): Promise<ScheduleResult> {
  return request<ScheduleResult>("/api/schedules/generate", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function approveSchedule(revisionId: number): Promise<{ revision_id: number; status: string }> {
  return request(`/api/schedules/${revisionId}/approve`, { method: "POST" });
}
