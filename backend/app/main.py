import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .demo_data import CONFLICT_GROUPS, DEMAND_GROUPS, OFFERINGS, ROOMS, SLOTS
from .models import GenerateScheduleRequest, GenerateScheduleResponse
from .repository import approve_revision, initialize_database, list_revisions
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
        return solve_schedule(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/schedules/{revision_id}/approve")
def approve_schedule(revision_id: int) -> dict[str, str | int]:
    if not approve_revision(revision_id):
        raise HTTPException(status_code=404, detail="نسخه برنامه پیدا نشد")
    return {"revision_id": revision_id, "status": "approved"}


@app.get("/api/schedules")
def revisions() -> list[dict]:
    return list_revisions()

