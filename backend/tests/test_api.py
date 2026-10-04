from itertools import combinations, product

from fastapi.testclient import TestClient

from app.demo_data import CONFLICT_GROUPS, DEMAND_GROUPS, OFFERINGS, ROOMS, SLOTS
from app.main import app
from app.models import SessionInput


def one_session(
    pattern: str = "every", fixed_slot_id: str | None = None
) -> list[SessionInput]:
    return [
        SessionInput(
            meeting_number=1,
            week_pattern=pattern,
            fixed_slot_id=fixed_slot_id,
        )
    ]


def week_layers(pattern: str) -> tuple[str, ...]:
    if pattern == "odd":
        return ("odd",)
    if pattern == "even":
        return ("even",)
    return ("odd", "even")


def sections_overlap(left: list[dict], right: list[dict]) -> bool:
    return any(
        left_item["slot"]["id"] == right_item["slot"]["id"]
        and bool(
            set(week_layers(left_item["week_pattern"]))
            & set(week_layers(right_item["week_pattern"]))
        )
        for left_item in left
        for right_item in right
    )


def demo_payload() -> dict:
    return {
        "name": "تست خودکار",
        "offerings": [item.model_dump() for item in OFFERINGS],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [item.model_dump() for item in ROOMS],
        "demand_groups": [item.model_dump() for item in DEMAND_GROUPS],
        "conflict_groups": [item.model_dump() for item in CONFLICT_GROUPS],
        "priority": {
            "course_ids": [],
            "semester": None,
            "strength": 4,
            "note": "آزادی معادلات دیفرانسیل و مهارت‌های نرم برای ترم ۷ بیشتر شود",
        },
    }


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_generate_demo_schedule() -> None:
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=demo_payload())
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "draft"
        assert len(data["assignments"]) == sum(len(item.sessions) for item in OFFERINGS)
        assert data["revision_id"] > 0
        assert 0 <= data["coverage_percent"] <= 100
        assert "دسته منع تداخل قطعی" in data["demand_basis"]
        assert any("درخواست فارسی" in insight for insight in data["insights"])
        assert all(assignment["room"] for assignment in data["assignments"])

        instructor_uses: set[tuple[str, str, str]] = set()
        room_uses: set[tuple[str, str, str]] = set()
        meetings_by_offering: dict[str, set[str]] = {}
        for assignment in data["assignments"]:
            for layer in week_layers(assignment["week_pattern"]):
                instructor_key = (
                    assignment["instructor"],
                    layer,
                    assignment["slot"]["id"],
                )
                assert instructor_key not in instructor_uses
                instructor_uses.add(instructor_key)
                room_key = (assignment["room"], layer, assignment["slot"]["id"])
                assert room_key not in room_uses
                room_uses.add(room_key)
            meetings_by_offering.setdefault(assignment["offering_id"], set()).add(
                assignment["slot"]["id"]
            )

        for offering in OFFERINGS:
            assert len(meetings_by_offering[offering.id]) == len(offering.sessions)

        assignments_by_offering: dict[str, list[dict]] = {}
        for assignment in data["assignments"]:
            assignments_by_offering.setdefault(assignment["offering_id"], []).append(
                assignment
            )
        offering_ids_by_course: dict[str, list[str]] = {}
        for offering in OFFERINGS:
            offering_ids_by_course.setdefault(offering.course_id, []).append(offering.id)
        for conflict_group in CONFLICT_GROUPS:
            choices = [
                offering_ids_by_course[course_id]
                for course_id in conflict_group.course_ids
            ]
            assert any(
                all(
                    not sections_overlap(
                        assignments_by_offering[left_id],
                        assignments_by_offering[right_id],
                    )
                    for left_id, right_id in combinations(path, 2)
                )
                for path in product(*choices)
            )


def test_reject_unknown_slot() -> None:
    payload = {
        "offerings": [{**OFFERINGS[0].model_dump(), "available_slot_ids": ["missing"]}],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [item.model_dump() for item in ROOMS],
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 422


def test_report_infeasible_instructor_schedule() -> None:
    first = OFFERINGS[0].model_copy(
        update={
            "id": "a-g1",
            "course_id": "a",
            "group_number": 1,
            "weekly_sessions": 1,
            "sessions": one_session(),
            "available_slot_ids": ["sat-08"],
        }
    )
    second = OFFERINGS[0].model_copy(
        update={
            "id": "b-g1",
            "course_id": "b",
            "group_number": 1,
            "weekly_sessions": 1,
            "sessions": one_session(),
            "available_slot_ids": ["sat-08"],
        }
    )
    payload = {
        "name": "سناریوی ناممکن",
        "offerings": [first.model_dump(), second.model_dump()],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [item.model_dump() for item in ROOMS],
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "infeasible"
        assert data["assignments"] == []


def test_report_missing_compatible_room() -> None:
    large = OFFERINGS[0].model_copy(
        update={"weekly_sessions": 1, "sessions": one_session(), "capacity": 300}
    )
    payload = {
        "name": "کلاس ناکافی",
        "offerings": [large.model_dump()],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [item.model_dump() for item in ROOMS],
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "infeasible"
        assert "هیچ کلاس سازگاری" in data["unresolved"][0]


def test_high_weight_demand_pair_is_kept_conflict_free() -> None:
    shared_slots = ["sat-08", "sat-10"]
    offerings = []
    for course_id, instructor in (
        ("priority-a", "teacher-a"),
        ("priority-b", "teacher-b"),
        ("flexible-c", "teacher-c"),
    ):
        offerings.append(
            OFFERINGS[0].model_copy(
                update={
                    "id": f"{course_id}-g1",
                    "course_id": course_id,
                    "code": course_id,
                    "title": course_id,
                    "instructor": instructor,
                    "group_number": 1,
                    "weekly_sessions": 1,
                    "sessions": one_session(),
                    "capacity": 30,
                    "available_slot_ids": shared_slots,
                }
            )
        )
    payload = {
        "name": "Demand-aware behavior",
        "offerings": [item.model_dump() for item in offerings],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [item.model_dump() for item in ROOMS],
        "demand_groups": [
            {
                "id": "important-pair",
                "label": "Important pair",
                "student_count": 100,
                "course_ids": ["priority-a", "priority-b"],
                "weight": 10,
                "source": "requested",
            },
            {
                "id": "small-pair",
                "label": "Small pair",
                "student_count": 1,
                "course_ids": ["priority-a", "flexible-c"],
                "weight": 1,
                "source": "estimated",
            },
        ],
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 200, response.text
        assignments = {
            assignment["course_id"]: assignment["slot"]["id"]
            for assignment in response.json()["assignments"]
        }
        assert assignments["priority-a"] != assignments["priority-b"]


def test_odd_and_even_groups_can_share_teacher_room_and_time() -> None:
    first = OFFERINGS[0].model_copy(
        update={
            "id": "rotating-a-g1",
            "course_id": "rotating-a",
            "weekly_sessions": 1,
            "week_pattern": "odd",
            "sessions": one_session("odd"),
            "available_slot_ids": ["sat-08"],
        }
    )
    second = OFFERINGS[0].model_copy(
        update={
            "id": "rotating-b-g1",
            "course_id": "rotating-b",
            "weekly_sessions": 1,
            "week_pattern": "even",
            "sessions": one_session("even"),
            "available_slot_ids": ["sat-08"],
        }
    )
    payload = {
        "offerings": [first.model_dump(), second.model_dump()],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [ROOMS[0].model_dump()],
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "draft"
        assert {item["week_pattern"] for item in data["assignments"]} == {"odd", "even"}
        assert len({item["slot"]["id"] for item in data["assignments"]}) == 1
        assert len({item["room"] for item in data["assignments"]}) == 1


def test_sessions_of_one_group_can_have_independent_patterns_and_fixed_times() -> None:
    offering = OFFERINGS[0].model_copy(
        update={
            "id": "mixed-session-g1",
            "course_id": "mixed-session",
            "weekly_sessions": 2,
            "week_pattern": "every",
            "sessions": [
                SessionInput(
                    meeting_number=1,
                    week_pattern="every",
                    fixed_slot_id="sat-08",
                ),
                SessionInput(
                    meeting_number=2,
                    week_pattern="odd",
                    fixed_slot_id="mon-10",
                ),
            ],
            "available_slot_ids": ["sat-08", "mon-10"],
        }
    )
    payload = {
        "offerings": [offering.model_dump()],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [ROOMS[0].model_dump()],
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 200, response.text
        assignments = {
            item["meeting_number"]: (item["week_pattern"], item["slot"]["id"])
            for item in response.json()["assignments"]
        }
        assert assignments == {
            1: ("every", "sat-08"),
            2: ("odd", "mon-10"),
        }


def test_fixed_session_time_must_be_in_teacher_availability() -> None:
    payload = demo_payload()
    payload["offerings"] = [
        {
            **OFFERINGS[1].model_dump(),
            "available_slot_ids": ["sat-08"],
            "sessions": [
                {
                    "meeting_number": 1,
                    "week_pattern": "every",
                    "fixed_slot_id": "mon-10",
                }
            ],
        }
    ]
    payload["demand_groups"] = []
    payload["conflict_groups"] = []
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 422
        assert "ساعت‌های آزاد استاد" in response.text


def test_strict_conflict_group_can_make_schedule_infeasible() -> None:
    first = OFFERINGS[0].model_copy(
        update={
            "id": "course-a-g1",
            "course_id": "course-a",
            "instructor": "teacher-a",
            "weekly_sessions": 1,
            "sessions": one_session(),
            "available_slot_ids": ["sat-08"],
        }
    )
    second = OFFERINGS[0].model_copy(
        update={
            "id": "course-b-g1",
            "course_id": "course-b",
            "instructor": "teacher-b",
            "weekly_sessions": 1,
            "sessions": one_session(),
            "available_slot_ids": ["sat-08"],
        }
    )
    payload = {
        "offerings": [first.model_dump(), second.model_dump()],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [item.model_dump() for item in ROOMS],
        "conflict_groups": [
            {
                "id": "entry-1403",
                "label": "ورودی ۱۴۰۳",
                "entry_year": "۱۴۰۳",
                "course_ids": ["course-a", "course-b"],
            }
        ],
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "infeasible"
