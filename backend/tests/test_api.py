from fastapi.testclient import TestClient

from app.demo_data import DEMAND_GROUPS, OFFERINGS, ROOMS, SLOTS
from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_generate_demo_schedule() -> None:
    payload = {
        "name": "تست خودکار",
        "offerings": [item.model_dump() for item in OFFERINGS],
        "slots": [item.model_dump() for item in SLOTS],
        "rooms": [item.model_dump() for item in ROOMS],
        "demand_groups": [item.model_dump() for item in DEMAND_GROUPS],
        "priority": {
            "course_ids": [],
            "semester": None,
            "strength": 4,
            "note": "آزادی معادلات دیفرانسیل و مهارت‌های نرم برای ترم ۷ بیشتر شود",
        },
    }
    with TestClient(app) as client:
        response = client.post("/api/schedules/generate", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "draft"
        assert len(data["assignments"]) == sum(item.groups for item in OFFERINGS)
        assert data["revision_id"] > 0
        assert 0 <= data["coverage_percent"] <= 100
        assert "سناریوی تقاضای برآوردی" in data["demand_basis"]
        assert any("درخواست فارسی" in insight for insight in data["insights"])
        assert all(assignment["room"] for assignment in data["assignments"])

        instructor_slots: set[tuple[str, str]] = set()
        room_slots: set[tuple[str, str]] = set()
        for assignment in data["assignments"]:
            key = (assignment["instructor"], assignment["slot"]["id"])
            assert key not in instructor_slots
            instructor_slots.add(key)
            room_key = (assignment["room"], assignment["slot"]["id"])
            assert room_key not in room_slots
            room_slots.add(room_key)


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
        update={"id": "a", "groups": 1, "available_slot_ids": ["sat-08"]}
    )
    second = OFFERINGS[0].model_copy(
        update={"id": "b", "groups": 1, "available_slot_ids": ["sat-08"]}
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
        assert data["coverage_percent"] == 0
        assert data["assignments"] == []


def test_report_missing_compatible_room() -> None:
    large = OFFERINGS[0].model_copy(update={"capacity": 300})
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
    first = OFFERINGS[0].model_copy(
        update={
            "id": "priority-a",
            "code": "A",
            "title": "A",
            "instructor": "teacher-a",
            "groups": 1,
            "capacity": 30,
            "available_slot_ids": shared_slots,
        }
    )
    second = OFFERINGS[0].model_copy(
        update={
            "id": "priority-b",
            "code": "B",
            "title": "B",
            "instructor": "teacher-b",
            "groups": 1,
            "capacity": 30,
            "available_slot_ids": shared_slots,
        }
    )
    third = OFFERINGS[0].model_copy(
        update={
            "id": "flexible-c",
            "code": "C",
            "title": "C",
            "instructor": "teacher-c",
            "groups": 1,
            "capacity": 30,
            "available_slot_ids": shared_slots,
        }
    )
    payload = {
        "name": "Demand-aware behavior",
        "offerings": [item.model_dump() for item in (first, second, third)],
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
            assignment["offering_id"]: assignment["slot"]["id"]
            for assignment in response.json()["assignments"]
        }
        assert assignments["priority-a"] != assignments["priority-b"]

