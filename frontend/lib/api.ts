import type { ConflictGroup, DemandGroup, DemoData, IntelligenceStatus, InterpretResult, Offering, Room, ScheduleResult, Slot } from "./types";

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

export function loadIntelligenceStatus(): Promise<IntelligenceStatus> {
  return request<IntelligenceStatus>("/api/intelligence/status");
}

export function interpretRequest(note: string, offerings: Offering[]): Promise<InterpretResult> {
  const courses = [...new Map(offerings.map((item) => [item.course_id, {
    course_id: item.course_id,
    code: item.code,
    title: item.title,
  }])).values()];
  return request<InterpretResult>("/api/ai/interpret", {
    method: "POST",
    body: JSON.stringify({ note, courses }),
  });
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

export function sendScheduleFeedback(revisionId: number, rating: number, comment = ""): Promise<{ status: string }> {
  return request(`/api/schedules/${revisionId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating, comment }),
  });
}

export function saveDemandHistory(records: Array<{ academic_term: string; course_id: string; enrolled_count: number; capacity: number }>): Promise<{ saved: number }> {
  return request("/api/demand/history", {
    method: "POST",
    body: JSON.stringify({ records }),
  });
}
