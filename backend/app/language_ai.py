from __future__ import annotations

import json
import os
import re

import httpx

from .models import CourseSummary, InterpretResponse


PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _heuristic(note: str, courses: list[CourseSummary]) -> InterpretResponse:
    normalized = note.replace("\u200c", " ")
    words = set(normalized.split())
    selected: list[str] = []
    for course in courses:
        title_words = [word for word in course.title.replace("\u200c", " ").split() if len(word) > 1]
        matches = sum(word in words for word in title_words)
        if course.title in note or course.code.lower() in note.lower() or (title_words and matches / len(title_words) >= 0.55):
            selected.append(course.course_id)
    semester_match = re.search(r"ترم\s*([1-8])", normalized.translate(PERSIAN_DIGITS))
    semester = int(semester_match.group(1)) if semester_match else None
    return InterpretResponse(
        course_ids=selected,
        semester=semester,
        strength=4 if any(word in note for word in ("خیلی", "بیشتر", "حتماً", "ضروری")) else 3,
        interpreted_text="درخواست با تحلیل داخلی فارسی به اولویت‌های قابل استفاده برای حل‌کننده تبدیل شد.",
        provider="heuristic",
    )


def interpret_persian_request(note: str, courses: list[CourseSummary]) -> InterpretResponse:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _heuristic(note, courses)

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    allowed_ids = {course.course_id for course in courses}
    course_catalog = [course.model_dump() for course in courses]
    prompt = (
        "تو دستیار مدیرگروه دانشگاه هستی. درخواست فارسی را فقط به اولویت زمان‌بندی تبدیل کن. "
        "فقط شناسه‌هایی را برگردان که در فهرست درس‌ها وجود دارند. ترم فقط ۱ تا ۸ یا null است. "
        "strength از ۱ تا ۵ است. هیچ برنامه زمانی تولید نکن؛ حل قطعی را OR-Tools انجام می‌دهد.\n"
        f"فهرست درس‌ها: {json.dumps(course_catalog, ensure_ascii=False)}\n"
        f"درخواست مدیرگروه: {note}"
    )
    schema = {
        "type": "OBJECT",
        "properties": {
            "course_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
            "semester": {"type": "INTEGER", "nullable": True},
            "strength": {"type": "INTEGER"},
            "interpreted_text": {"type": "STRING"},
        },
        "required": ["course_ids", "semester", "strength", "interpreted_text"],
    }
    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": schema,
                    "temperature": 0.1,
                },
            },
            timeout=20,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        semester = parsed.get("semester")
        if semester not in range(1, 9):
            semester = None
        return InterpretResponse(
            course_ids=[course_id for course_id in parsed.get("course_ids", []) if course_id in allowed_ids],
            semester=semester,
            strength=max(1, min(5, int(parsed.get("strength", 3)))),
            interpreted_text=str(parsed.get("interpreted_text", "درخواست با Gemini تحلیل شد.")),
            provider="gemini",
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _heuristic(note, courses)
