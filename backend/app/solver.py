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


def _interpreted_priority(request: GenerateScheduleRequest) -> tuple[set[str], int | None]:
    """Extract supported course names and a semester number from the Persian request."""
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
        fuzzy_title_match = word_matches >= 2 and word_matches / len(title_words) >= 0.6
        if (
            offering.title in note
            or offering.code.lower() in note.lower()
            or fuzzy_title_match
        ):
            priority_ids.add(offering.id)

    semester = request.priority.semester
    normalized_note = note.translate(PERSIAN_DIGITS)
    semester_match = re.search(r"ترم\s*([1-8])", normalized_note)
    if semester_match:
        semester = int(semester_match.group(1))
    return priority_ids, semester


def _default_demands(offerings: list[OfferingInput]) -> list[DemandGroup]:
    by_semester: dict[int, list[str]] = defaultdict(list)
    for offering in offerings:
        by_semester[offering.preferred_semester].append(offering.id)
    return [
        DemandGroup(
            id=f"semester-{semester}",
            label=f"چارت پیشنهادی ترم {semester}",
            student_count=1,
            course_ids=course_ids,
            weight=5,
            source="estimated",
        )
        for semester, course_ids in by_semester.items()
        if len(course_ids) >= 2
    ]


def solve_schedule(request: GenerateScheduleRequest) -> GenerateScheduleResponse:
    for offering in request.offerings:
        if offering.groups > len(offering.available_slot_ids):
            return _infeasible_response(
                request.name,
                f"درس «{offering.title}» {offering.groups} گروه دارد اما فقط {len(offering.available_slot_ids)} زمان متفاوت برای استاد ثبت شده است.",
            )

    offerings_by_instructor: dict[str, list[OfferingInput]] = defaultdict(list)
    for offering in request.offerings:
        offerings_by_instructor[offering.instructor].append(offering)
    for instructor, instructor_offerings in offerings_by_instructor.items():
        required_sections = sum(offering.groups for offering in instructor_offerings)
        available_slots = {
            slot_id
            for offering in instructor_offerings
            for slot_id in offering.available_slot_ids
        }
        if required_sections > len(available_slots):
            return _infeasible_response(
                request.name,
                f"{instructor} باید {required_sections} گروه ارائه دهد اما فقط {len(available_slots)} بازه غیرهم‌زمان دارد.",
            )

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
        offering.title
        for offering in request.offerings
        if not compatible_rooms[offering.id]
    ]
    if without_room:
        return _infeasible_response(
            request.name,
            f"برای ظرفیت یا نوع درس «{'، '.join(without_room)}» هیچ کلاس سازگاری وجود ندارد.",
        )

    model = cp_model.CpModel()
    slot_by_id = {slot.id: slot for slot in request.slots}
    room_by_id = {room.id: room for room in request.rooms}
    sections: list[tuple[str, OfferingInput, int]] = []
    sections_by_course: dict[str, list[str]] = defaultdict(list)
    variables: dict[tuple[str, str], cp_model.IntVar] = {}
    placements: dict[tuple[str, str, str], cp_model.IntVar] = {}

    for offering in request.offerings:
        for group_number in range(1, offering.groups + 1):
            section_id = f"{offering.id}-g{group_number}"
            sections.append((section_id, offering, group_number))
            sections_by_course[offering.id].append(section_id)
            section_placements: list[cp_model.IntVar] = []
            for slot_id in offering.available_slot_ids:
                variables[(section_id, slot_id)] = model.new_bool_var(f"x_{section_id}_{slot_id}")
                slot_placements: list[cp_model.IntVar] = []
                for room in compatible_rooms[offering.id]:
                    placement = model.new_bool_var(
                        f"place_{section_id}_{slot_id}_{room.id}"
                    )
                    placements[(section_id, slot_id, room.id)] = placement
                    slot_placements.append(placement)
                    section_placements.append(placement)
                model.add(
                    variables[(section_id, slot_id)] == sum(slot_placements)
                )
            model.add_exactly_one(section_placements)

            locked_slot = request.locked_assignments.get(offering.id)
            if locked_slot:
                if locked_slot not in offering.available_slot_ids:
                    raise ValueError(f"زمان قفل‌شده برای {offering.title} در دسترس استاد نیست")
                # قفل درس روی گروه اول اعمال می‌شود و گروه‌های دیگر آزادی ایجاد می‌کنند.
                if group_number == 1:
                    model.add(variables[(section_id, locked_slot)] == 1)

    # محدودیت قطعی: استاد در یک بازه فقط یک کلاس دارد.
    by_instructor_slot: dict[tuple[str, str], list[cp_model.IntVar]] = defaultdict(list)
    for section_id, offering, _ in sections:
        for slot_id in offering.available_slot_ids:
            by_instructor_slot[(offering.instructor, slot_id)].append(
                variables[(section_id, slot_id)]
            )
    for vars_at_time in by_instructor_slot.values():
        model.add(sum(vars_at_time) <= 1)

    # گروه‌های موازی یک درس باید در زمان‌های متفاوت باشند.
    by_course_slot: dict[tuple[str, str], list[cp_model.IntVar]] = defaultdict(list)
    for section_id, offering, _ in sections:
        for slot_id in offering.available_slot_ids:
            by_course_slot[(offering.id, slot_id)].append(variables[(section_id, slot_id)])
    for vars_at_time in by_course_slot.values():
        model.add(sum(vars_at_time) <= 1)

    # محدودیت قطعی: یک کلاس یا آزمایشگاه در یک زمان فقط به یک گروه اختصاص دارد.
    for slot in request.slots:
        for room in request.rooms:
            room_uses = [
                placement
                for (section_id, slot_id, room_id), placement in placements.items()
                if slot_id == slot.id and room_id == room.id
            ]
            if room_uses:
                model.add(sum(room_uses) <= 1)

    offering_by_id = {offering.id: offering for offering in request.offerings}
    section_offering = {section_id: offering for section_id, offering, _ in sections}
    same_time_cache: dict[tuple[str, str], cp_model.IntVar] = {}

    def same_time(left_section: str, right_section: str) -> cp_model.IntVar:
        key = tuple(sorted((left_section, right_section)))
        if key in same_time_cache:
            return same_time_cache[key]
        left = section_offering[left_section]
        right = section_offering[right_section]
        shared_slots = set(left.available_slot_ids) & set(right.available_slot_ids)
        collisions: list[cp_model.IntVar] = []
        for slot_id in shared_slots:
            collision = model.new_bool_var(
                f"collision_{key[0]}_{key[1]}_{slot_id}"
            )
            left_var = variables[(left_section, slot_id)]
            right_var = variables[(right_section, slot_id)]
            model.add(collision <= left_var)
            model.add(collision <= right_var)
            model.add(collision >= left_var + right_var - 1)
            collisions.append(collision)
        same = model.new_bool_var(f"same_{key[0]}_{key[1]}")
        model.add(same == sum(collisions)) if collisions else model.add(same == 0)
        same_time_cache[key] = same
        return same

    priority_ids, priority_semester = _interpreted_priority(request)
    demands = request.demand_groups or _default_demands(request.offerings)
    penalties: list[cp_model.LinearExpr] = []
    demand_conflicts: list[tuple[DemandGroup, str, str, cp_model.IntVar, int]] = []

    # هر جفت درس برای یک گروه تقاضا قابل اخذ است اگر حداقل یک جفت گروه غیرهم‌زمان وجود داشته باشد.
    for demand in demands:
        available_courses = [course_id for course_id in demand.course_ids if course_id in offering_by_id]
        for left_course, right_course in combinations(available_courses, 2):
            pair_same_vars = [
                same_time(left_section, right_section)
                for left_section in sections_by_course[left_course]
                for right_section in sections_by_course[right_course]
            ]
            unavoidable = model.new_bool_var(
                f"unavoidable_{demand.id}_{left_course}_{right_course}"
            )
            model.add_bool_and(pair_same_vars).only_enforce_if(unavoidable)
            model.add_bool_or([value.Not() for value in pair_same_vars]).only_enforce_if(
                unavoidable.Not()
            )
            pair_weight = demand.student_count * demand.weight
            if left_course in priority_ids or right_course in priority_ids:
                pair_weight += demand.student_count * request.priority.strength * 2
            penalties.append(pair_weight * unavoidable)
            demand_conflicts.append(
                (demand, left_course, right_course, unavoidable, pair_weight)
            )

    # درخواست «آزادی بیشتر برای درس X در ترم Y» حتی بدون داده تاریخی اثر می‌گذارد.
    if priority_semester is not None:
        target_courses = [
            offering.id
            for offering in request.offerings
            if offering.preferred_semester == priority_semester
        ]
        for priority_course in priority_ids:
            for target_course in target_courses:
                if priority_course == target_course:
                    continue
                pair_same_vars = [
                    same_time(left_section, right_section)
                    for left_section in sections_by_course[priority_course]
                    for right_section in sections_by_course[target_course]
                ]
                unavoidable = model.new_bool_var(
                    f"priority_{priority_course}_{target_course}"
                )
                model.add_bool_and(pair_same_vars).only_enforce_if(unavoidable)
                model.add_bool_or(
                    [value.Not() for value in pair_same_vars]
                ).only_enforce_if(unavoidable.Not())
                penalties.append(request.priority.strength * 100 * unavoidable)

    # ترجیح نرم: گروه‌های دروس یک ترم تا حد امکان روی هم نیفتند.
    for left_id, right_id in combinations(offering_by_id, 2):
        left = offering_by_id[left_id]
        right = offering_by_id[right_id]
        if left.preferred_semester != right.preferred_semester:
            continue
        for left_section in sections_by_course[left_id]:
            for right_section in sections_by_course[right_id]:
                penalties.append(2 * same_time(left_section, right_section))

    model.minimize(sum(penalties) if penalties else 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 12
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _infeasible_response(
            request.name,
            "با زمان‌های آزاد، ظرفیت کلاس‌ها و تعداد گروه‌های فعلی برنامه شدنی نیست؛ یکی از این محدودیت‌ها را تغییر دهید.",
        )

    assignments: list[ScheduleAssignment] = []
    for section_id, offering, group_number in sections:
        selected_slot = next(
            slot_by_id[slot_id]
            for slot_id in offering.available_slot_ids
            if solver.value(variables[(section_id, slot_id)])
        )
        selected_room = next(
            room_by_id[room.id]
            for room in compatible_rooms[offering.id]
            if solver.value(placements[(section_id, selected_slot.id, room.id)])
        )
        assignments.append(
            ScheduleAssignment(
                section_id=section_id,
                offering_id=offering.id,
                code=offering.code,
                course_title=offering.title,
                instructor=offering.instructor,
                group_number=group_number,
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
    demand_by_course = {
        offering.id: sum(
            demand.student_count
            for demand in demands
            if offering.id in demand.course_ids
        )
        for offering in request.offerings
    }
    total_requested_seats = sum(demand_by_course.values())
    covered_seats = sum(
        min(demand_by_course[offering.id], offering.groups * offering.capacity)
        for offering in request.offerings
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
                f"برای «{demand.label}»، {offering_by_id[left_id].title} با {offering_by_id[right_id].title} مسیر بدون تداخل ندارد."
            )
    for offering in request.offerings:
        demand_count = demand_by_course[offering.id]
        available_capacity = offering.groups * offering.capacity
        if demand_count > available_capacity:
            suggested_groups = (demand_count + offering.capacity - 1) // offering.capacity
            unresolved.append(
                f"«{offering.title}» حدود {demand_count} متقاضی و {available_capacity} صندلی دارد؛ حداقل {suggested_groups} گروه پیشنهاد می‌شود."
            )

    priority_titles = [
        offering.title for offering in request.offerings if offering.id in priority_ids
    ]
    historical_count = sum(1 for demand in demands if demand.source == "historical")
    demand_basis = (
        f"{len(demands)} گروه تقاضا؛ {historical_count} گروه مبتنی بر سابقه واقعی"
        if historical_count
        else f"{len(demands)} سناریوی تقاضای برآوردی؛ هنوز بدون آمار واقعی دانشگاه"
    )
    insights = [
        f"برای {len(assignments)} گروه درسی زمان قابل اجرا پیدا شد.",
        f"پوشش زمانی جفت‌درس‌ها {conflict_coverage}٪ و پوشش ظرفیت صندلی‌ها {capacity_coverage}٪ محاسبه شد.",
        "گروه‌های موازی هر درس در زمان‌های متفاوت قرار گرفتند تا مسیر جایگزین ایجاد شود.",
    ]
    if priority_titles:
        insights.append(
            f"درخواست فارسی برای «{'، '.join(priority_titles)}» به اولویت حل‌کننده تبدیل شد."
        )
    if priority_semester:
        insights.append(f"دروس ترم {priority_semester} در آزادی انتخاب وزن بیشتری گرفتند.")

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
            Metric(label="پوشش انتخاب", value=f"{coverage}٪", change="برآورد جفت‌درس‌های قابل اخذ", tone="mint"),
            Metric(label="گروه‌های چیده‌شده", value=str(len(assignments)), change="بدون تداخل استاد", tone="blue"),
            Metric(label="تداخل حل‌نشده", value=str(len(unresolved)), change="استاد، کلاس و تقاضا", tone="peach"),
        ],
        insights=insights,
        unresolved=unresolved,
    )
