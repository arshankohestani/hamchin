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
  code: string;
  title: string;
  instructor: string;
  preferred_semester: number;
  groups: number;
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

export type Assignment = {
  section_id: string;
  offering_id: string;
  code: string;
  course_title: string;
  instructor: string;
  group_number: number;
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
  revisions: Array<{ id: number; name: string; status: string; score: number; created_at: string }>;
};

