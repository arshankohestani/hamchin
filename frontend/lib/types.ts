export type Slot = {
  id: string;
  day: string;
  start: string;
  end: string;
  label: string;
};

export type Room = {
  id: string;
  name: string;
  capacity: number;
  kind: "classroom" | "lab";
};

export type Offering = {
  id: string;
  course_id: string;
  code: string;
  title: string;
  instructor: string;
  preferred_semester: number;
  group_number: number;
  weekly_sessions: number;
  week_pattern: "every" | "odd" | "even";
  capacity: number;
  available_slot_ids: string[];
  flexibility: number;
  kind: "theory" | "lab" | "skill";
  enabled?: boolean;
};

export type DemandGroup = {
  id: string;
  label: string;
  student_count: number;
  course_ids: string[];
  weight: number;
  source: "estimated" | "historical" | "requested";
};

export type ConflictGroup = {
  id: string;
  label: string;
  entry_year: string;
  course_ids: string[];
};

export type Assignment = {
  section_id: string;
  offering_id: string;
  course_id: string;
  code: string;
  course_title: string;
  instructor: string;
  group_number: number;
  meeting_number: number;
  week_pattern: "every" | "odd" | "even";
  capacity: number;
  semester: number;
  kind: string;
  slot: Slot;
  room: string | null;
};

export type ScheduleResult = {
  revision_id: number;
  name: string;
  status: string;
  score: number;
  coverage_percent: number;
  demand_basis: string;
  assignments: Assignment[];
  metrics: Array<{
    label: string;
    value: string;
    change: string;
    tone: "mint" | "lavender" | "peach" | "blue";
  }>;
  insights: string[];
  unresolved: string[];
};

export type DemoData = {
  slots: Slot[];
  rooms: Room[];
  offerings: Offering[];
  demand_groups: DemandGroup[];
  conflict_groups: ConflictGroup[];
  revisions: Array<{ id: number; name: string; status: string; score: number; created_at: string }>;
};

