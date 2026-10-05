from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime

import pandas as pd
from catboost import CatBoostRanker, CatBoostRegressor, Pool

from app.repository import (
    demand_training_rows,
    feedback_training_rows,
    save_model_metadata,
    upsert_demand_forecasts,
)


def parse_term(value: str) -> tuple[int, int]:
    numbers = [int(item) for item in re.findall(r"\d+", value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))]
    return (numbers[0] if numbers else 0, numbers[1] if len(numbers) > 1 else 1)


def train_demand(target_term: str) -> dict:
    rows = demand_training_rows()
    if len(rows) < 8 or len({row["academic_term"] for row in rows}) < 2:
        return {"status": "waiting_for_data", "needed": "حداقل ۸ رکورد از دو نیم‌سال"}
    frame = pd.DataFrame(rows)
    terms = frame["academic_term"].map(parse_term)
    frame["year"] = terms.map(lambda item: item[0])
    frame["semester"] = terms.map(lambda item: item[1])
    features = frame[["course_id", "year", "semester", "capacity"]]
    model = CatBoostRegressor(iterations=250, depth=6, learning_rate=0.05, loss_function="RMSE", verbose=False, random_seed=42)
    model.fit(features, frame["enrolled_count"], cat_features=["course_id"])

    target_year, target_semester = parse_term(target_term)
    latest = frame.sort_values(["year", "semester"]).groupby("course_id", as_index=False).tail(1)
    predict_frame = pd.DataFrame({
        "course_id": latest["course_id"],
        "year": target_year,
        "semester": target_semester,
        "capacity": latest["capacity"],
    })
    predictions = model.predict(predict_frame)
    version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    records = [
        {
            "academic_term": target_term,
            "course_id": str(course_id),
            "predicted_count": max(0, round(float(prediction))),
            "model_name": "CatBoostRegressor",
            "model_version": version,
        }
        for course_id, prediction in zip(predict_frame["course_id"], predictions, strict=True)
    ]
    upsert_demand_forecasts(records)
    metadata = {"version": version, "training_rows": len(rows), "forecast_count": len(records), "target_term": target_term}
    save_model_metadata("demand-catboost", metadata)
    return {"status": "trained", **metadata}


def revision_features(payload: dict) -> list[float]:
    assignments = payload.get("assignments", [])
    starts = [int(item.get("slot", {}).get("start", "08:00")[:2]) for item in assignments]
    late_ratio = sum(start >= 16 for start in starts) / max(1, len(starts))
    rotating_ratio = sum(item.get("week_pattern") != "every" for item in assignments) / max(1, len(assignments))
    return [
        float(payload.get("score", 0)),
        float(payload.get("coverage_percent", 0)),
        float(len(assignments)),
        late_ratio,
        rotating_ratio,
        sum(starts) / max(1, len(starts)),
    ]


def train_preferences() -> dict:
    rows = feedback_training_rows()
    if len(rows) < 5 or len({row["rating"] for row in rows}) < 2:
        return {"status": "waiting_for_data", "needed": "حداقل ۵ امتیاز با دست‌کم دو مقدار متفاوت"}
    payloads = [row["payload"] if isinstance(row["payload"], dict) else __import__("json").loads(row["payload"]) for row in rows]
    features = [revision_features(payload) for payload in payloads]
    labels = [row["rating"] for row in rows]
    feature_names = ["score", "coverage", "meetings", "late_ratio", "rotating_ratio", "average_hour"]
    pool = Pool(features, label=labels, group_id=[0] * len(rows), feature_names=feature_names)
    model = CatBoostRanker(iterations=180, depth=5, learning_rate=0.05, loss_function="YetiRank", verbose=False, random_seed=42)
    model.fit(pool)
    version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    metadata = {
        "version": version,
        "training_rows": len(rows),
        "feature_importance": dict(zip(feature_names, [round(float(value), 4) for value in model.get_feature_importance(pool)], strict=True)),
    }
    save_model_metadata("manager-catboost-ranker", metadata)
    return {"status": "trained", **metadata}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Hamchin free CatBoost models")
    parser.add_argument("--target-term", required=True, help="Example: 1405-1")
    arguments = parser.parse_args()
    print({"demand": train_demand(arguments.target_term), "preferences": train_preferences()})
