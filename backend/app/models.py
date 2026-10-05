from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TimeSlot(BaseModel):
    id: str
    day: str
    start: str
    end: str
    label: str


class RoomInput(BaseModel):
    id: str
    name: str
    capacity: int = Field(ge=5, le=1_000)
    kind: Literal["classroom", "lab"] = "classroom"


class SessionInput(BaseModel):
    meeting_number: int = Field(ge=1, le=6)
    week_pattern: Literal["every", "odd", "even"] = "every"
    fixed_slot_id: str | None = None


class OfferingInput(BaseModel):
    id: str
    course_id: str = ""
    code: str
    title: str
    instructor: str
    preferred_semester: int = Field(ge=1, le=8)
    group_number: int = Field(default=1, ge=1, le=99)
    weekly_sessions: int = Field(default=1, ge=1, le=6)
    week_pattern: Literal["every", "odd", "even"] = "every"
    sessions: list[SessionInput] = Field(default_factory=list, max_length=6)
    capacity: int = Field(default=35, ge=5, le=300)
    available_slot_ids: list[str] = Field(default_factory=list)
    flexibility: int = Field(default=3, ge=1, le=5)
    kind: Literal["theory", "lab", "skill"] = "theory"

    @model_validator(mode="after")
    def normalize_course_and_sessions(self) -> "OfferingInput":
        if not self.course_id:
            self.course_id = self.id
        if not self.sessions:
            self.sessions = [
                SessionInput(
                    meeting_number=number,
                    week_pattern=self.week_pattern,
                )
                for number in range(1, self.weekly_sessions + 1)
            ]
        meeting_numbers = [session.meeting_number for session in self.sessions]
        if len(set(meeting_numbers)) != len(meeting_numbers):
            raise ValueError("شماره جلسه‌های هر گروه باید یکتا باشد")
        self.sessions.sort(key=lambda session: session.meeting_number)
        self.weekly_sessions = len(self.sessions)
        self.week_pattern = self.sessions[0].week_pattern
        return self


class PriorityRequest(BaseModel):
    course_ids: list[str] = Field(default_factory=list)
    semester: int | None = Field(default=None, ge=1, le=8)
    strength: int = Field(default=3, ge=1, le=5)
    note: str = ""
    interpretation_source: Literal["heuristic", "gemini", "manual"] = "manual"


class DemandGroup(BaseModel):
    id: str
    label: str
    student_count: int = Field(ge=1, le=10_000)
    course_ids: list[str] = Field(min_length=1)
    weight: int = Field(default=1, ge=1, le=10)
    source: Literal["estimated", "historical", "requested"] = "estimated"


class ConflictGroup(BaseModel):
    id: str
    label: str
    entry_year: str = ""
    course_ids: list[str] = Field(min_length=2)


class GenerateScheduleRequest(BaseModel):
    name: str = "سناریوی پیشنهادی"
    offerings: list[OfferingInput] = Field(min_length=1)
    slots: list[TimeSlot] = Field(min_length=1)
    rooms: list[RoomInput] = Field(min_length=1)
    priority: PriorityRequest = Field(default_factory=PriorityRequest)
    demand_groups: list[DemandGroup] = Field(default_factory=list)
    conflict_groups: list[ConflictGroup] = Field(default_factory=list)
    locked_assignments: dict[str, str] = Field(default_factory=dict)
    learned_slot_preferences: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> "GenerateScheduleRequest":
        without_availability = [
            f"{offering.title} (گروه {offering.group_number})"
            for offering in self.offerings
            if not offering.available_slot_ids
        ]
        if without_availability:
            raise ValueError(
                "برای این ارائه‌ها هنوز زمان آزاد استاد انتخاب نشده است: "
                + "، ".join(without_availability)
            )
        slot_ids = {slot.id for slot in self.slots}
        unknown = {
            slot_id
            for offering in self.offerings
            for slot_id in offering.available_slot_ids
            if slot_id not in slot_ids
        }
        if unknown:
            raise ValueError(f"زمان‌های ناشناخته: {sorted(unknown)}")
        unknown_fixed_slots = {
            session.fixed_slot_id
            for offering in self.offerings
            for session in offering.sessions
            if session.fixed_slot_id and session.fixed_slot_id not in slot_ids
        }
        if unknown_fixed_slots:
            raise ValueError(f"زمان ثابت ناشناخته: {sorted(unknown_fixed_slots)}")
        unavailable_fixed_slots = [
            f"{offering.title}، گروه {offering.group_number}، جلسه {session.meeting_number}"
            for offering in self.offerings
            for session in offering.sessions
            if session.fixed_slot_id
            and session.fixed_slot_id not in offering.available_slot_ids
        ]
        if unavailable_fixed_slots:
            raise ValueError(
                "زمان ثابت جلسه باید جزو ساعت‌های آزاد استاد باشد: "
                + "، ".join(unavailable_fixed_slots)
            )
        offering_ids = {offering.id for offering in self.offerings}
        if len(offering_ids) != len(self.offerings):
            raise ValueError("شناسه ارائه‌ها باید یکتا باشد")
        section_keys = {
            (offering.course_id, offering.group_number)
            for offering in self.offerings
        }
        if len(section_keys) != len(self.offerings):
            raise ValueError("شماره گروه هر درس باید یکتا باشد")
        course_ids = {offering.course_id for offering in self.offerings}
        if len({room.id for room in self.rooms}) != len(self.rooms):
            raise ValueError("شناسه کلاس‌ها باید یکتا باشد")
        unknown_courses = {
            course_id
            for group in self.demand_groups
            for course_id in group.course_ids
            if course_id not in course_ids
        }
        unknown_conflict_courses = {
            course_id
            for group in self.conflict_groups
            for course_id in group.course_ids
            if course_id not in course_ids
        }
        if unknown_courses:
            raise ValueError(f"درس‌های ناشناخته در تقاضا: {sorted(unknown_courses)}")
        if unknown_conflict_courses:
            raise ValueError(
                f"درس‌های ناشناخته در دسته منع تداخل: {sorted(unknown_conflict_courses)}"
            )
        bad_locks = set(self.locked_assignments) - offering_ids
        if bad_locks:
            raise ValueError(f"قفل مربوط به درس ناشناخته است: {sorted(bad_locks)}")
        return self


class ScheduleAssignment(BaseModel):
    section_id: str
    offering_id: str
    course_id: str
    code: str
    course_title: str
    instructor: str
    group_number: int
    meeting_number: int
    week_pattern: Literal["every", "odd", "even"]
    capacity: int
    semester: int
    kind: str
    slot: TimeSlot
    room: str | None = None


class Metric(BaseModel):
    label: str
    value: str
    change: str
    tone: Literal["mint", "lavender", "peach", "blue"]


class ScheduleProgram(BaseModel):
    id: str
    label: str
    semester: int | None
    assignments: list[ScheduleAssignment]


class GenerateScheduleResponse(BaseModel):
    revision_id: int
    name: str
    status: str
    score: int
    coverage_percent: int
    demand_basis: str
    assignments: list[ScheduleAssignment]
    schedule_programs: list[ScheduleProgram]
    metrics: list[Metric]
    insights: list[str]
    unresolved: list[str]


class CourseSummary(BaseModel):
    course_id: str
    code: str
    title: str


class InterpretRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2_000)
    courses: list[CourseSummary]


class InterpretResponse(BaseModel):
    course_ids: list[str]
    semester: int | None = Field(default=None, ge=1, le=8)
    strength: int = Field(default=3, ge=1, le=5)
    interpreted_text: str
    provider: Literal["gemini", "heuristic"]


class DemandHistoryItem(BaseModel):
    academic_term: str = Field(min_length=1, max_length=30)
    course_id: str = Field(min_length=1, max_length=120)
    enrolled_count: int = Field(ge=0, le=100_000)
    capacity: int = Field(default=0, ge=0, le=100_000)


class DemandHistoryRequest(BaseModel):
    records: list[DemandHistoryItem] = Field(min_length=1, max_length=10_000)


class ScheduleFeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1_000)


class IntelligenceStatus(BaseModel):
    solver: str
    persian_understanding: str
    database: str
    demand_forecasting: str
    preference_learning: str
