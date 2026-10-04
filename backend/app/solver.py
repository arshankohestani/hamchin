from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations

from ortools.sat.python import cp_model

from .models import (
    DemandGroup,
    GenerateScheduleRequest,
    GenerateScheduleResponse,
    Metric,
    OfferingInput,
    ScheduleAssignment,
    SessionInput,
)
from .repository import save_revision


PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _infeasible_response(name: str, message: str) -> GenerateScheduleResponse:
    return GenerateScheduleResponse(
        revision_id=0,
        name=name,
        status="infeasible",
        score=0,
        coverage_percent=0,
        demand_basis="برنامه ناممکن",
        assignments=[],
        metrics=[],
        insights=[],
        unresolved=[message],
    )


def _active_layers(pattern: str) -> tuple[str, ...]:
    if pattern == "odd":
        return ("odd",)
    if pattern == "even":
        return ("even",)
    return ("odd", "even")


def _weeks_overlap(left: str, right: str) -> bool:
    return bool(set(_active_layers(left)) & set(_active_layers(right)))


def _interpreted_priority(request: GenerateScheduleRequest) -> tuple[set[str], int | None]:
    """Extract supported course names and a semester number from a Persian request."""
    note = request.priority.note.strip()
    normalized_note_words = set(note.replace("\u200c", " ").split())
    priority_ids = set(request.priority.course_ids)
    for offering in request.offerings:
        title_words = [
            word
            for word in offering.title.replace("\u200c", " ").split()
            if word not in {"و", "های", "در", "با"}
        ]
        word_matches = sum(word in normalized_note_words for word in title_words)
        fuzzy_title_match = bool(title_words) and word_matches >= 2 and word_matches / len(title_words) >= 0.6
        if offering.title in note or offering.code.lower() in note.lower() or fuzzy_title_match:
            priority_ids.add(offering.course_id)

    semester = request.priority.semester
    normalized_note = note.translate(PERSIAN_DIGITS)
    semester_match = re.search(r"ترم\s*([1-8])", normalized_note)
    if semester_match:
        semester = int(semester_match.group(1))
    return priority_ids, semester


def _default_demands(offerings: list[OfferingInput]) -> list[DemandGroup]:
    by_semester: dict[int, set[str]] = defaultdict(set)
    for offering in offerings:
        by_semester[offering.preferred_semester].add(offering.course_id)
    return [
        DemandGroup(
            id=f"semester-{semester}",
            label=f"چارت پیشنهادی ترم {semester}",
            student_count=1,
            course_ids=sorted(course_ids),
            weight=5,
            source="estimated",
        )
        for semester, course_ids in by_semester.items()
        if len(course_ids) >= 2
    ]


def solve_schedule(request: GenerateScheduleRequest) -> GenerateScheduleResponse:
    compatible_rooms = {
        offering.id: [
            room
            for room in request.rooms
            if room.capacity >= offering.capacity
            and (offering.kind != "lab" or room.kind == "lab")
        ]
        for offering in request.offerings
    }
    without_room = [
        f"{offering.title}، گروه {offering.group_number}"
        for offering in request.offerings
        if not compatible_rooms[offering.id]
    ]
    if without_room:
        return _infeasible_response(
            request.name,
            f"برای ظرفیت یا نوع ارائهٔ «{'، '.join(without_room)}» هیچ کلاس سازگاری وجود ندارد.",
        )

    model = cp_model.CpModel()
    slot_by_id = {slot.id: slot for slot in request.slots}
    room_by_id = {room.id: room for room in request.rooms}
    offering_by_id = {offering.id: offering for offering in request.offerings}
    offerings_by_course: dict[str, list[str]] = defaultdict(list)
    for offering in request.offerings:
        offerings_by_course[offering.course_id].append(offering.id)

    meetings: list[tuple[str, OfferingInput, SessionInput]] = []
    meetings_by_offering: dict[str, list[str]] = defaultdict(list)
    meeting_offering: dict[str, OfferingInput] = {}
    meeting_session: dict[str, SessionInput] = {}
    meeting_slots: dict[str, list[str]] = {}
    variables: dict[tuple[str, str], cp_model.IntVar] = {}
    placements: dict[tuple[str, str, str], cp_model.IntVar] = {}
    penalties: list[cp_model.LinearExpr] = []

    for offering in request.offerings:
        for session in offering.sessions:
            meeting_id = f"{offering.id}-m{session.meeting_number}"
            allowed_slots = (
                [session.fixed_slot_id]
                if session.fixed_slot_id
                else list(dict.fromkeys(offering.available_slot_ids))
            )
            meetings.append((meeting_id, offering, session))
            meetings_by_offering[offering.id].append(meeting_id)
            meeting_offering[meeting_id] = offering
            meeting_session[meeting_id] = session
            meeting_slots[meeting_id] = allowed_slots
            meeting_placements: list[cp_model.IntVar] = []
            for slot_id in allowed_slots:
                variables[(meeting_id, slot_id)] = model.new_bool_var(
                    f"x_{meeting_id}_{slot_id}"
                )
                slot_placements: list[cp_model.IntVar] = []
                for room in compatible_rooms[offering.id]:
                    placement = model.new_bool_var(
                        f"place_{meeting_id}_{slot_id}_{room.id}"
                    )
                    placements[(meeting_id, slot_id, room.id)] = placement
                    slot_placements.append(placement)
                    meeting_placements.append(placement)
                    if offering.kind != "lab" and room.kind == "lab":
                        penalties.append(3 * placement)
                model.add(variables[(meeting_id, slot_id)] == sum(slot_placements))
            model.add_exactly_one(meeting_placements)

            locked_slot = request.locked_assignments.get(meeting_id)
            if session.meeting_number == 1:
                locked_slot = locked_slot or request.locked_assignments.get(offering.id)
            if locked_slot:
                if locked_slot not in allowed_slots:
                    raise ValueError(
                        f"زمان قفل‌شده برای جلسه {session.meeting_number} درس {offering.title} مجاز نیست"
                    )
                model.add(variables[(meeting_id, locked_slot)] == 1)

    # جلسات یک گروه فقط زمانی می‌توانند یک ساعت مشترک داشته باشند که هفته‌هایشان هم‌پوشانی نداشته باشد.
    for offering in request.offerings:
        for layer in ("odd", "even"):
            for slot_id in offering.available_slot_ids:
                uses = [
                    variables[(meeting_id, slot_id)]
                    for meeting_id in meetings_by_offering[offering.id]
                    if layer in _active_layers(meeting_session[meeting_id].week_pattern)
                    and slot_id in meeting_slots[meeting_id]
                ]
                if uses:
                    model.add(sum(uses) <= 1)

    # هفته زوج و فرد دو لایه مستقل‌اند؛ «هر هفته» در هر دو لایه حضور دارد.
    by_instructor_layer_slot: dict[tuple[str, str, str], list[cp_model.IntVar]] = defaultdict(list)
    for meeting_id, offering, session in meetings:
        for layer in _active_layers(session.week_pattern):
            for slot_id in meeting_slots[meeting_id]:
                by_instructor_layer_slot[(offering.instructor, layer, slot_id)].append(
                    variables[(meeting_id, slot_id)]
                )
    for uses in by_instructor_layer_slot.values():
        model.add(sum(uses) <= 1)

    by_room_layer_slot: dict[tuple[str, str, str], list[cp_model.IntVar]] = defaultdict(list)
    for (meeting_id, slot_id, room_id), placement in placements.items():
        session = meeting_session[meeting_id]
        for layer in _active_layers(session.week_pattern):
            by_room_layer_slot[(room_id, layer, slot_id)].append(placement)
    for uses in by_room_layer_slot.values():
        model.add(sum(uses) <= 1)

    section_conflict_cache: dict[tuple[str, str], cp_model.IntVar] = {}

    def sections_conflict(left_id: str, right_id: str) -> cp_model.IntVar:
        key = tuple(sorted((left_id, right_id)))
        if key in section_conflict_cache:
            return section_conflict_cache[key]
        left = offering_by_id[key[0]]
        right = offering_by_id[key[1]]
        collisions: list[cp_model.IntVar] = []
        for left_meeting in meetings_by_offering[left.id]:
            for right_meeting in meetings_by_offering[right.id]:
                left_session = meeting_session[left_meeting]
                right_session = meeting_session[right_meeting]
                if _weeks_overlap(left_session.week_pattern, right_session.week_pattern):
                    shared_slots = set(meeting_slots[left_meeting]) & set(
                        meeting_slots[right_meeting]
                    )
                    for slot_id in shared_slots:
                        collision = model.new_bool_var(
                            f"collision_{left_meeting}_{right_meeting}_{slot_id}"
                        )
                        left_var = variables[(left_meeting, slot_id)]
                        right_var = variables[(right_meeting, slot_id)]
                        model.add(collision <= left_var)
                        model.add(collision <= right_var)
                        model.add(collision >= left_var + right_var - 1)
                        collisions.append(collision)
        conflict = model.new_bool_var(f"section_conflict_{key[0]}_{key[1]}")
        if collisions:
            model.add_max_equality(conflict, collisions)
        else:
            model.add(conflict == 0)
        section_conflict_cache[key] = conflict
        return conflict

    # برای هر دستهٔ منع تداخل، حل‌کننده یک گروه از هر درس انتخاب می‌کند که همگی با هم قابل اخذ باشند.
    for conflict_group in request.conflict_groups:
        selected: dict[tuple[str, str], cp_model.IntVar] = {}
        present_courses = [
            course_id
            for course_id in dict.fromkeys(conflict_group.course_ids)
            if course_id in offerings_by_course
        ]
        for course_id in present_courses:
            selectors = []
            for offering_id in offerings_by_course[course_id]:
                selector = model.new_bool_var(
                    f"path_{conflict_group.id}_{course_id}_{offering_id}"
                )
                selected[(course_id, offering_id)] = selector
                selectors.append(selector)
            model.add_exactly_one(selectors)
        for left_course, right_course in combinations(present_courses, 2):
            for left_id in offerings_by_course[left_course]:
                for right_id in offerings_by_course[right_course]:
                    model.add(sections_conflict(left_id, right_id) == 0).only_enforce_if(
                        [
                            selected[(left_course, left_id)],
                            selected[(right_course, right_id)],
                        ]
                    )

    priority_ids, priority_semester = _interpreted_priority(request)
    demands = request.demand_groups or _default_demands(request.offerings)
    demand_conflicts: list[tuple[DemandGroup, str, str, cp_model.IntVar, int]] = []

    for demand in demands:
        available_courses = [
            course_id for course_id in demand.course_ids if course_id in offerings_by_course
        ]
        for left_course, right_course in combinations(available_courses, 2):
            pair_conflicts = [
                sections_conflict(left_id, right_id)
                for left_id in offerings_by_course[left_course]
                for right_id in offerings_by_course[right_course]
            ]
            unavoidable = model.new_bool_var(
                f"unavoidable_{demand.id}_{left_course}_{right_course}"
            )
            model.add_bool_and(pair_conflicts).only_enforce_if(unavoidable)
            model.add_bool_or([value.Not() for value in pair_conflicts]).only_enforce_if(
                unavoidable.Not()
            )
            pair_weight = demand.student_count * demand.weight
            if left_course in priority_ids or right_course in priority_ids:
                pair_weight += demand.student_count * request.priority.strength * 2
            penalties.append(pair_weight * unavoidable)
            demand_conflicts.append(
                (demand, left_course, right_course, unavoidable, pair_weight)
            )

    if priority_semester is not None:
        target_courses = {
            offering.course_id
            for offering in request.offerings
            if offering.preferred_semester == priority_semester
        }
        for priority_course in priority_ids:
            if priority_course not in offerings_by_course:
                continue
            for target_course in target_courses:
                if priority_course == target_course:
                    continue
                pair_conflicts = [
                    sections_conflict(left_id, right_id)
                    for left_id in offerings_by_course[priority_course]
                    for right_id in offerings_by_course[target_course]
                ]
                unavoidable = model.new_bool_var(
                    f"priority_{priority_course}_{target_course}"
                )
                model.add_bool_and(pair_conflicts).only_enforce_if(unavoidable)
                model.add_bool_or(
                    [value.Not() for value in pair_conflicts]
                ).only_enforce_if(unavoidable.Not())
                penalties.append(request.priority.strength * 100 * unavoidable)

    # گروه‌های موازی یک درس ترجیحاً مسیرهای زمانی متفاوت ایجاد می‌کنند.
    for offering_ids in offerings_by_course.values():
        for left_id, right_id in combinations(offering_ids, 2):
            penalties.append(5 * sections_conflict(left_id, right_id))

    courses_by_semester: dict[int, set[str]] = defaultdict(set)
    for offering in request.offerings:
        courses_by_semester[offering.preferred_semester].add(offering.course_id)
    for course_ids in courses_by_semester.values():
        for left_course, right_course in combinations(sorted(course_ids), 2):
            for left_id in offerings_by_course[left_course]:
                for right_id in offerings_by_course[right_course]:
                    penalties.append(2 * sections_conflict(left_id, right_id))

    model.minimize(sum(penalties) if penalties else 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 12
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _infeasible_response(
            request.name,
            "با جلسات، الگوی هفته‌های زوج و فرد، ساعت استادها، کلاس‌ها و دسته‌های منع تداخل فعلی برنامه شدنی نیست؛ یکی از این محدودیت‌ها را تغییر دهید.",
        )

    assignments: list[ScheduleAssignment] = []
    for meeting_id, offering, session in meetings:
        selected_slot = next(
            slot_by_id[slot_id]
            for slot_id in meeting_slots[meeting_id]
            if solver.value(variables[(meeting_id, slot_id)])
        )
        selected_room = next(
            room_by_id[room.id]
            for room in compatible_rooms[offering.id]
            if solver.value(placements[(meeting_id, selected_slot.id, room.id)])
        )
        assignments.append(
            ScheduleAssignment(
                section_id=meeting_id,
                offering_id=offering.id,
                course_id=offering.course_id,
                code=offering.code,
                course_title=offering.title,
                instructor=offering.instructor,
                group_number=offering.group_number,
                meeting_number=session.meeting_number,
                week_pattern=session.week_pattern,
                capacity=offering.capacity,
                semester=offering.preferred_semester,
                kind=offering.kind,
                slot=selected_slot,
                room=selected_room.name,
            )
        )

    total_weight = sum(item[4] for item in demand_conflicts)
    conflict_weight = sum(
        pair_weight
        for _, _, _, conflict_var, pair_weight in demand_conflicts
        if solver.value(conflict_var)
    )
    conflict_coverage = (
        round(100 * (total_weight - conflict_weight) / total_weight)
        if total_weight
        else 100
    )
    course_titles = {
        course_id: offering_by_id[offering_ids[0]].title
        for course_id, offering_ids in offerings_by_course.items()
    }
    demand_by_course = {
        course_id: sum(
            demand.student_count
            for demand in demands
            if course_id in demand.course_ids
        )
        for course_id in offerings_by_course
    }
    capacity_by_course = {
        course_id: sum(offering_by_id[item_id].capacity for item_id in offering_ids)
        for course_id, offering_ids in offerings_by_course.items()
    }
    total_requested_seats = sum(demand_by_course.values())
    covered_seats = sum(
        min(demand_by_course[course_id], capacity_by_course[course_id])
        for course_id in offerings_by_course
    )
    capacity_coverage = (
        round(100 * covered_seats / total_requested_seats)
        if total_requested_seats
        else 100
    )
    coverage = min(conflict_coverage, capacity_coverage)
    score = max(0, min(100, coverage - min(10, int(solver.objective_value // 500))))
    unresolved: list[str] = []
    for demand, left_id, right_id, conflict_var, _ in demand_conflicts:
        if solver.value(conflict_var):
            unresolved.append(
                f"برای «{demand.label}»، {course_titles[left_id]} با {course_titles[right_id]} مسیر بدون تداخل ندارد."
            )
    for course_id, demand_count in demand_by_course.items():
        available_capacity = capacity_by_course[course_id]
        if demand_count > available_capacity:
            max_capacity = max(
                offering_by_id[item_id].capacity
                for item_id in offerings_by_course[course_id]
            )
            suggested_groups = (demand_count + max_capacity - 1) // max_capacity
            unresolved.append(
                f"«{course_titles[course_id]}» حدود {demand_count} متقاضی و {available_capacity} صندلی دارد؛ حداقل {suggested_groups} گروه پیشنهاد می‌شود."
            )

    priority_titles = sorted(
        {course_titles[course_id] for course_id in priority_ids if course_id in course_titles}
    )
    historical_count = sum(1 for demand in demands if demand.source == "historical")
    demand_basis = (
        f"{len(demands)} گروه تقاضا؛ {historical_count} گروه مبتنی بر سابقه واقعی؛ {len(request.conflict_groups)} دسته منع تداخل قطعی"
        if historical_count
        else f"{len(demands)} سناریوی تقاضای برآوردی؛ {len(request.conflict_groups)} دسته منع تداخل قطعی؛ هنوز بدون آمار واقعی دانشگاه"
    )
    rotating_count = sum(
        1
        for offering in request.offerings
        for session in offering.sessions
        if session.week_pattern != "every"
    )
    insights = [
        f"برای {len(request.offerings)} گروه درسی، {len(assignments)} جلسه قابل اجرا پیدا شد.",
        f"پوشش زمانی جفت‌درس‌ها {conflict_coverage}٪ و پوشش ظرفیت صندلی‌ها {capacity_coverage}٪ محاسبه شد.",
        f"برای {len(request.conflict_groups)} دسته، یک مسیر کامل بدون تداخل میان همه درس‌های دسته تضمین شد.",
    ]
    if rotating_count:
        insights.append(
            f"{rotating_count} جلسه چرخشی زوج/فرد با تفکیک واقعی هفته‌ها زمان‌بندی شد."
        )
    if priority_titles:
        insights.append(
            f"درخواست فارسی برای «{'، '.join(priority_titles)}» به اولویت حل‌کننده تبدیل شد."
        )
    if priority_semester:
        insights.append(
            f"دروس ترم {priority_semester} در آزادی انتخاب وزن بیشتری گرفتند."
        )

    response_payload = {
        "name": request.name,
        "score": score,
        "coverage_percent": coverage,
        "demand_basis": demand_basis,
        "assignments": [assignment.model_dump() for assignment in assignments],
    }
    revision_id = save_revision(request.name, score, response_payload)
    return GenerateScheduleResponse(
        revision_id=revision_id,
        name=request.name,
        status="draft",
        score=score,
        coverage_percent=coverage,
        demand_basis=demand_basis,
        assignments=assignments,
        metrics=[
            Metric(label="کیفیت چینش", value=f"{score}٪", change="براساس محدودیت و تقاضا", tone="lavender"),
            Metric(label="پوشش انتخاب", value=f"{coverage}٪", change="برآورد مسیرهای قابل اخذ", tone="mint"),
            Metric(label="جلسات چیده‌شده", value=str(len(assignments)), change=f"برای {len(request.offerings)} گروه درسی", tone="blue"),
            Metric(label="موارد قابل بهبود", value=str(len(unresolved)), change="ظرفیت و تقاضای نرم", tone="peach"),
        ],
        insights=insights,
        unresolved=unresolved,
    )
