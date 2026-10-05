import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .demo_data import CONFLICT_GROUPS, DEMAND_GROUPS, OFFERINGS, ROOMS, SLOTS
from .language_ai import interpret_persian_request
from .models import (
    CourseSummary,
    DemandGroup,
    DemandHistoryRequest,
    GenerateScheduleRequest,
    GenerateScheduleResponse,
    IntelligenceStatus,
    InterpretRequest,
    InterpretResponse,
    ScheduleFeedbackRequest,
)
from .repository import (
    approve_revision,
    database_provider,
    get_demand_forecasts,
    get_preference,
    initialize_database,
    list_revisions,
    save_demand_history,
    save_feedback,
)
from .solver import solve_schedule


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="هم‌چین API",
    description="هسته نسخه اولیه دستیار هوشمند مدیرگروه",
    version="0.1.0",
    lifespan=lifespan,
)

configured_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *configured_origins,
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "hamchin-api"}


@app.get("/api/intelligence/status", response_model=IntelligenceStatus)
def intelligence_status() -> IntelligenceStatus:
    gemini_ready = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    target_term = os.environ.get("ML_TARGET_TERM", "1405-1")
    forecasts = get_demand_forecasts(target_term)
    preferences = get_preference("slot_scores")
    return IntelligenceStatus(
        solver="OR-Tools CP-SAT فعال",
        persian_understanding="Gemini فعال" if gemini_ready else "تحلیل داخلی فعال؛ کلید Gemini تنظیم نشده",
        database="Neon Postgres فعال" if database_provider() == "neon-postgres" else "SQLite محلی؛ DATABASE_URL تنظیم نشده",
        demand_forecasting=f"CatBoost فعال؛ {len(forecasts)} پیش‌بینی برای {target_term}" if forecasts else "منتظر داده تاریخی و اجرای worker CatBoost",
        preference_learning=f"یادگیری فعال؛ {len(preferences)} ترجیح زمانی" if preferences else "منتظر تأیید یا امتیاز مدیرگروه",
    )


@app.get("/api/demo")
def demo() -> dict:
    return {
        "slots": [slot.model_dump() for slot in SLOTS],
        "rooms": [room.model_dump() for room in ROOMS],
        "offerings": [offering.model_dump() for offering in OFFERINGS],
        "demand_groups": [group.model_dump() for group in DEMAND_GROUPS],
        "conflict_groups": [group.model_dump() for group in CONFLICT_GROUPS],
        "revisions": list_revisions(),
    }


@app.post("/api/schedules/generate", response_model=GenerateScheduleResponse)
def generate_schedule(request: GenerateScheduleRequest) -> GenerateScheduleResponse:
    try:
        if request.priority.note.strip():
            courses = {
                offering.course_id: CourseSummary(
                    course_id=offering.course_id,
                    code=offering.code,
                    title=offering.title,
                )
                for offering in request.offerings
            }
            interpreted = interpret_persian_request(request.priority.note, list(courses.values()))
            request.priority.course_ids = sorted(set(request.priority.course_ids) | set(interpreted.course_ids))
            request.priority.semester = request.priority.semester or interpreted.semester
            request.priority.strength = max(request.priority.strength, interpreted.strength)
            request.priority.interpretation_source = interpreted.provider

        target_term = os.environ.get("ML_TARGET_TERM", "1405-1")
        forecasts = get_demand_forecasts(target_term)
        active_course_ids = {offering.course_id for offering in request.offerings}
        if forecasts:
            requested_groups = [group for group in request.demand_groups if group.source == "requested"]
            request.demand_groups = requested_groups + [
                DemandGroup(
                    id=f"catboost-{target_term}-{item['course_id']}",
                    label=f"پیش‌بینی CatBoost برای {item['course_id']}",
                    student_count=item["predicted_count"],
                    course_ids=[item["course_id"]],
                    weight=6,
                    source="historical",
                )
                for item in forecasts
                if item["course_id"] in active_course_ids
            ]
        request.learned_slot_preferences = {
            slot_id: int(score)
            for slot_id, score in get_preference("slot_scores").items()
            if slot_id in {slot.id for slot in request.slots}
        }
        return solve_schedule(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/ai/interpret", response_model=InterpretResponse)
def interpret_request(request: InterpretRequest) -> InterpretResponse:
    return interpret_persian_request(request.note, request.courses)


@app.post("/api/demand/history")
def add_demand_history(request: DemandHistoryRequest) -> dict[str, int]:
    return {"saved": save_demand_history([record.model_dump() for record in request.records])}


@app.get("/api/demand/forecasts")
def demand_forecasts(academic_term: str | None = None) -> list[dict]:
    return get_demand_forecasts(academic_term or os.environ.get("ML_TARGET_TERM", "1405-1"))


@app.post("/api/schedules/{revision_id}/approve")
def approve_schedule(revision_id: int) -> dict[str, str | int]:
    if not approve_revision(revision_id):
        raise HTTPException(status_code=404, detail="نسخه برنامه پیدا نشد")
    save_feedback(revision_id, 5, "تأیید نهایی مدیرگروه")
    return {"revision_id": revision_id, "status": "approved"}


@app.post("/api/schedules/{revision_id}/feedback")
def schedule_feedback(revision_id: int, request: ScheduleFeedbackRequest) -> dict[str, str | int]:
    if not save_feedback(revision_id, request.rating, request.comment):
        raise HTTPException(status_code=404, detail="نسخه برنامه پیدا نشد")
    return {"revision_id": revision_id, "status": "learned", "rating": request.rating}


@app.get("/api/schedules")
def revisions() -> list[dict]:
    return list_revisions()

