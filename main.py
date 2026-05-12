"""
WA-PSS Scoring API v3.0 — Full Inclusive Build
================================================
Wearable-Augmented Perceived Stress Scale.

Design principles
-----------------
- Gender identity, biological sex, and menstruation status are captured as
  three independent fields. SQ12 (menstrual-cycle data concern) is
  administered to anyone who menstruates, regardless of gender identity.
- Wearable biomarkers are ingested via /v1/biometrics and auto-merged into
  the scoring response when a respondent_id is supplied.
- Longitudinal trajectory is exposed via /v1/dashboard/{respondent_id}.
- Four-class LCA phenotype framework is declared; actual classification
  centroids are part of the proprietary commercial-tier algorithm.

Licensing
---------
- Scale items: CC BY-NC 4.0
- LCA classification algorithm + centroids: Proprietary (commercial license)
- Wearable SDK field mappings: open documentation

© Dr. Rohan J. Kosambiya, 2026 — NAMO Medical Education and Research Institute
Contact: rjkosambiya@gmail.com
Validation paper: Indian Journal of Psychological Medicine (in submission)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timezone
from collections import defaultdict
import os

# ═══════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="WA-PSS Scoring API",
    version="3.0.0",
    description=(
        "Wearable-Augmented Perceived Stress Scale — inclusive, "
        "clinically grounded scoring engine with wearable biomarker ingestion, "
        "longitudinal trajectory tracking, and LCA-based stress phenotyping framework. "
        "Scale items CC BY-NC 4.0; classification algorithm proprietary."
    ),
    contact={
        "name": "Dr. Rohan J. Kosambiya",
        "email": "rjkosambiya@gmail.com",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
# ENUMS — inclusive profile fields
# ═══════════════════════════════════════════════════════════════════

class GenderIdentity(str, Enum):
    MAN = "man"
    WOMAN = "woman"
    NON_BINARY = "non_binary"
    TRANS_MAN = "trans_man"
    TRANS_WOMAN = "trans_woman"
    GENDERQUEER = "genderqueer"
    AGENDER = "agender"
    SELF_DESCRIBE = "self_describe"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class BiologicalSex(str, Enum):
    AFAB = "assigned_female_at_birth"
    AMAB = "assigned_male_at_birth"
    INTERSEX = "intersex"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class SeverityBand(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class WearablePlatform(str, Enum):
    APPLE_HEALTHKIT = "apple_healthkit"
    COROS = "coros"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    SAMSUNG_HEALTH = "samsung_health"
    POLAR = "polar"
    OTHER = "other"


# ═══════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════

class ScoreRequest(BaseModel):
    respondent_id: Optional[str] = Field(
        None,
        description="Optional client-supplied identifier. Enables longitudinal tracking "
                    "and auto-merge of biometric data into the scoring response.",
    )
    age: int = Field(..., ge=13, le=100)
    gender_identity: GenderIdentity
    self_described_gender: Optional[str] = Field(
        None, description="Required if gender_identity='self_describe'"
    )
    biological_sex: Optional[BiologicalSex] = None
    menstruates: bool = Field(
        ...,
        description="Independent of gender identity. Controls SQ12 administration.",
    )

    # Items — PSS-derived (SQ1–SQ10), wearable-augmented (SQ11), conditional (SQ12)
    sq1: int = Field(..., ge=0, le=4)
    sq2: int = Field(..., ge=0, le=4)
    sq3: int = Field(..., ge=0, le=4)
    sq4: int = Field(..., ge=0, le=4)
    sq5: int = Field(..., ge=0, le=4)
    sq6: int = Field(..., ge=0, le=4)
    sq7: int = Field(..., ge=0, le=4)
    sq8: int = Field(..., ge=0, le=4)
    sq9: int = Field(..., ge=0, le=4)
    sq10: int = Field(..., ge=0, le=4)
    sq11: int = Field(..., ge=0, le=4, description="I trust the health data on my wearable")
    sq12: Optional[int] = Field(
        None,
        ge=0,
        le=4,
        description="I worry about menstrual-cycle data on my device (required if menstruates=True)",
    )

    @model_validator(mode="after")
    def validate_conditional_items(self):
        if self.gender_identity == GenderIdentity.SELF_DESCRIBE and not self.self_described_gender:
            raise ValueError("self_described_gender is required when gender_identity='self_describe'")
        if self.menstruates and self.sq12 is None:
            raise ValueError("sq12 is required when menstruates=True")
        if not self.menstruates and self.sq12 is not None:
            raise ValueError("sq12 must be omitted when menstruates=False")
        return self


class BiometricSnapshot(BaseModel):
    respondent_id: str = Field(..., description="Required. Links biometric data to respondent.")
    platform: WearablePlatform
    timestamp_utc: Optional[datetime] = None

    # Cardiovascular
    resting_hr_bpm: Optional[float] = Field(None, ge=20, le=220)
    hrv_rmssd_ms: Optional[float] = Field(None, ge=0, le=500)
    spo2_pct: Optional[float] = Field(None, ge=50, le=100)

    # Sleep
    sleep_total_hours: Optional[float] = Field(None, ge=0, le=24)
    sleep_efficiency_pct: Optional[float] = Field(None, ge=0, le=100)
    deep_sleep_minutes: Optional[float] = Field(None, ge=0, le=600)
    rem_sleep_minutes: Optional[float] = Field(None, ge=0, le=600)

    # Activity
    daily_steps: Optional[int] = Field(None, ge=0, le=100000)
    active_minutes: Optional[int] = Field(None, ge=0, le=1440)
    vo2max_ml_kg_min: Optional[float] = Field(None, ge=10, le=90)

    # Device-derived stress / recovery proxies
    device_stress_score: Optional[float] = Field(None, ge=0, le=100, description="Garmin/COROS/Fitbit stress score")
    body_battery: Optional[float] = Field(None, ge=0, le=100, description="Garmin/COROS recovery proxy")
    readiness_score: Optional[float] = Field(None, ge=0, le=100)


# ═══════════════════════════════════════════════════════════════════
# IN-MEMORY STORES (Phase 1 — Postgres in Phase 2)
# ═══════════════════════════════════════════════════════════════════

score_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
biometric_store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


# ═══════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════

REVERSE_ITEMS = {"sq4", "sq5", "sq7", "sq8"}


def reverse_score(value: int, max_value: int = 4) -> int:
    return max_value - value


def latest_biometrics(respondent_id: str) -> Optional[Dict[str, Any]]:
    if respondent_id and respondent_id in biometric_store and biometric_store[respondent_id]:
        return biometric_store[respondent_id][-1]
    return None


def lca_phenotype_stub() -> Dict[str, Any]:
    """
    Four-class LCA stress phenotype framework declaration.
    The classifier itself (centroids, posterior probabilities, class labels)
    is part of the proprietary commercial-tier algorithm, with class
    structure derived from the IJPM validation cohort (n in submission).
    """
    return {
        "framework": "Four-class latent class analysis (LCA) stress phenotype",
        "classification": "available_in_commercial_tier",
        "note": (
            "Class assignment, posterior class probabilities, and phenotype "
            "labels are part of the proprietary algorithm. Commercial license "
            "required. Contact rjkosambiya@gmail.com."
        ),
        "validation": "WA-PSS validation paper in submission to Indian Journal of Psychological Medicine",
    }


def score_payload(req: ScoreRequest) -> Dict[str, Any]:
    items = {
        "sq1": req.sq1, "sq2": req.sq2, "sq3": req.sq3, "sq4": req.sq4,
        "sq5": req.sq5, "sq6": req.sq6, "sq7": req.sq7, "sq8": req.sq8,
        "sq9": req.sq9, "sq10": req.sq10, "sq11": req.sq11,
    }
    if req.menstruates:
        items["sq12"] = req.sq12

    scored = {k: (reverse_score(v) if k in REVERSE_ITEMS else v) for k, v in items.items()}

    pss_core_keys = [f"sq{i}" for i in range(1, 11)]
    pss_total = sum(scored[k] for k in pss_core_keys)
    wa_total = sum(scored.values())
    n_items = len(scored)
    normalized = wa_total / (n_items * 4)

    if normalized < 0.35:
        severity = SeverityBand.LOW
    elif normalized < 0.65:
        severity = SeverityBand.MODERATE
    else:
        severity = SeverityBand.HIGH

    bio = latest_biometrics(req.respondent_id) if req.respondent_id else None

    response = {
        "scoring": {
            "pss_core_total": pss_total,
            "pss_core_range": "0–40",
            "wa_total": wa_total,
            "wa_total_range": f"0–{n_items * 4}",
            "normalized": round(normalized, 3),
            "severity_band": severity.value,
            "items_administered": n_items,
            "reverse_scored": sorted(REVERSE_ITEMS),
        },
        "profile_meta": {
            "gender_identity": req.gender_identity.value,
            "self_described_gender": req.self_described_gender,
            "biological_sex": req.biological_sex.value if req.biological_sex else None,
            "menstruates": req.menstruates,
            "sq12_administered": req.menstruates,
            "age": req.age,
        },
        "biometric_merge": {
            "merged": bio is not None,
            "latest_biometric": bio,
        },
        "phenotype": lca_phenotype_stub(),
        "licensing": {
            "scale_items": "CC BY-NC 4.0",
            "scoring_algorithm": "Proprietary — commercial license for production use",
            "wearable_mappings": "Open documentation",
            "citation": (
                "Kosambiya RJ. Wearable-Augmented Perceived Stress Scale (WA-PSS), v3.0. "
                "2026. Validation paper: Indian Journal of Psychological Medicine (in submission)."
            ),
        },
        "respondent_id": req.respondent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to history if respondent_id supplied
    if req.respondent_id:
        score_history[req.respondent_id].append({
            "timestamp": response["timestamp"],
            "wa_total": wa_total,
            "pss_core_total": pss_total,
            "normalized": round(normalized, 3),
            "severity_band": severity.value,
            "items_administered": n_items,
        })

    return response


# ═══════════════════════════════════════════════════════════════════
# SDK FIELD MAPPINGS — for partner integrations
# ═══════════════════════════════════════════════════════════════════

SDK_FIELD_MAPPINGS = {
    "apple_healthkit": {
        "resting_hr_bpm": "HKQuantityTypeIdentifierRestingHeartRate",
        "hrv_rmssd_ms": "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "spo2_pct": "HKQuantityTypeIdentifierOxygenSaturation",
        "sleep_total_hours": "HKCategoryTypeIdentifierSleepAnalysis (asleep duration)",
        "daily_steps": "HKQuantityTypeIdentifierStepCount",
        "active_minutes": "HKQuantityTypeIdentifierAppleExerciseTime",
        "vo2max_ml_kg_min": "HKQuantityTypeIdentifierVO2Max",
    },
    "coros": {
        "resting_hr_bpm": "rhr",
        "hrv_rmssd_ms": "hrv",
        "sleep_total_hours": "sleep.totalSleepTime",
        "deep_sleep_minutes": "sleep.deepSleep",
        "rem_sleep_minutes": "sleep.remSleep",
        "daily_steps": "steps",
        "vo2max_ml_kg_min": "vo2max",
        "body_battery": "energy",
        "endpoint": "COROS Training Hub API v3",
    },
    "garmin": {
        "resting_hr_bpm": "restingHeartRate",
        "hrv_rmssd_ms": "hrvWeeklyAverage",
        "sleep_total_hours": "sleepTimeSeconds / 3600",
        "daily_steps": "steps",
        "device_stress_score": "averageStressLevel",
        "body_battery": "bodyBatteryHighestValue",
        "endpoint": "Garmin Connect Health API",
    },
    "fitbit": {
        "resting_hr_bpm": "activities-heart.value.restingHeartRate",
        "hrv_rmssd_ms": "hrv.value.dailyRmssd",
        "spo2_pct": "spo2.value.avg",
        "sleep_total_hours": "sleep.summary.totalMinutesAsleep / 60",
        "daily_steps": "activities-steps.value",
        "device_stress_score": "stress.score",
        "readiness_score": "readiness.score",
    },
    "samsung_health": {
        "resting_hr_bpm": "com.samsung.shealth.tracker.heart_rate (resting)",
        "spo2_pct": "com.samsung.shealth.tracker.oxygen_saturation",
        "sleep_total_hours": "com.samsung.shealth.sleep",
        "daily_steps": "com.samsung.shealth.tracker.pedometer_step_count",
    },
    "polar": {
        "resting_hr_bpm": "resting-heart-rate",
        "hrv_rmssd_ms": "nightly-recharge.heart-rate-variability-avg",
        "sleep_total_hours": "sleep.sleep-duration",
        "daily_steps": "activity-summary.steps",
        "readiness_score": "nightly-recharge.recharge-status",
        "endpoint": "Polar AccessLink API v3",
    },
}


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "name": "WA-PSS Scoring API",
        "version": "3.0.0",
        "status": "live",
        "build": "full_v3_inclusive",
        "endpoints": {
            "score": "POST /v1/score",
            "biometrics": "POST /v1/biometrics",
            "dashboard": "GET /v1/dashboard/{respondent_id}",
            "scale": "GET /v1/scale",
            "sdk_mappings": "GET /v1/sdk-mappings",
            "health": "GET /v1/health",
            "docs": "GET /docs",
        },
        "features": [
            "LGBTQIA+-inclusive profile capture (decoupled gender identity, biological sex, menstruation)",
            "Conditional SQ12 administration based on menstruation status (not gender)",
            "Wearable biometric ingestion (Apple, COROS, Garmin, Fitbit, Samsung, Polar)",
            "Auto-merge of latest biometrics into scoring responses",
            "Longitudinal score trajectory per respondent",
            "Four-class LCA stress phenotype framework",
            "Dual-tier licensing: scale CC BY-NC 4.0, algorithm proprietary",
        ],
        "license": {
            "scale": "CC BY-NC 4.0",
            "algorithm": "Proprietary",
            "mappings": "Open documentation",
        },
        "contact": "rjkosambiya@gmail.com",
    }


@app.post("/v1/score")
async def score(req: ScoreRequest):
    try:
        return score_payload(req)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/v1/biometrics")
async def ingest_biometrics(snapshot: BiometricSnapshot):
    """
    Ingest a wearable biometric snapshot. Auto-merged into the respondent's
    next /v1/score call. Snapshots are stored per respondent_id.
    """
    if snapshot.timestamp_utc is None:
        snapshot.timestamp_utc = datetime.now(timezone.utc)

    record = snapshot.model_dump(mode="json")
    biometric_store[snapshot.respondent_id].append(record)

    return {
        "status": "stored",
        "respondent_id": snapshot.respondent_id,
        "platform": snapshot.platform.value,
        "snapshot_count_for_respondent": len(biometric_store[snapshot.respondent_id]),
        "stored_record": record,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/dashboard/{respondent_id}")
async def dashboard(respondent_id: str):
    """
    Longitudinal trajectory for a respondent: score history + biometric trends.
    Intended for clinician-facing dashboards and research follow-up.
    """
    scores = score_history.get(respondent_id, [])
    biometrics = biometric_store.get(respondent_id, [])

    if not scores and not biometrics:
        raise HTTPException(
            status_code=404,
            detail=f"No data on file for respondent_id='{respondent_id}'",
        )

    # Trajectory summary
    if scores:
        wa_totals = [s["wa_total"] for s in scores]
        trajectory = {
            "n_assessments": len(scores),
            "first_assessment": scores[0]["timestamp"],
            "latest_assessment": scores[-1]["timestamp"],
            "wa_total_first": wa_totals[0],
            "wa_total_latest": wa_totals[-1],
            "wa_total_change": wa_totals[-1] - wa_totals[0],
            "wa_total_mean": round(sum(wa_totals) / len(wa_totals), 2),
            "severity_band_latest": scores[-1]["severity_band"],
        }
    else:
        trajectory = None

    return {
        "respondent_id": respondent_id,
        "score_trajectory": trajectory,
        "score_history": scores,
        "biometric_snapshots": biometrics,
        "biometric_snapshot_count": len(biometrics),
        "phenotype": lca_phenotype_stub(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/scale")
async def scale():
    return {
        "instrument": "Wearable-Augmented Perceived Stress Scale (WA-PSS)",
        "version": "3.0.0",
        "license": "CC BY-NC 4.0 (items only — algorithm proprietary)",
        "design": {
            "profile_fields": {
                "gender_identity": {
                    "type": "enum",
                    "options": [g.value for g in GenderIdentity],
                    "note": "9 options including self_describe and prefer_not_to_say",
                },
                "biological_sex": {
                    "type": "enum (optional)",
                    "options": [s.value for s in BiologicalSex],
                    "note": "Used only when clinically relevant (e.g., pharmacogenomic dosing)",
                },
                "menstruates": {
                    "type": "boolean",
                    "note": "Independent of gender identity. Controls SQ12 administration.",
                },
            },
            "core_items": "SQ1–SQ10 (PSS-derived, wearable-contextualized)",
            "augmented_item": "SQ11 (wearable trust) — administered to all",
            "conditional_item": "SQ12 (menstrual-cycle data concern) — administered if menstruates=True",
            "response_scale": "0 (never) – 4 (very often)",
            "reverse_scored": ["sq4", "sq5", "sq7", "sq8"],
        },
        "items": [
            {"id": "SQ1", "text": "Upset by unexpected changes in your health-metric data", "reverse": False},
            {"id": "SQ2", "text": "Unable to control important health metrics shown by your device", "reverse": False},
            {"id": "SQ3", "text": "Nervous or stressed about what your health data shows", "reverse": False},
            {"id": "SQ4", "text": "Confident in handling health problems flagged by your device", "reverse": True},
            {"id": "SQ5", "text": "Things going your way with your health goals", "reverse": True},
            {"id": "SQ6", "text": "Could not cope with the health demands and alerts you faced", "reverse": False},
            {"id": "SQ7", "text": "Able to control irritations caused by device alerts", "reverse": True},
            {"id": "SQ8", "text": "On top of your health-monitoring goals", "reverse": True},
            {"id": "SQ9", "text": "Angered by things outside your control in your health metrics", "reverse": False},
            {"id": "SQ10", "text": "Health goals piling up beyond what you can manage", "reverse": False},
            {"id": "SQ11", "text": "I trust the health data on my wearable device", "reverse": False, "applies_to": "all"},
            {"id": "SQ12", "text": "I worry about the menstrual-cycle data on my device", "reverse": False, "applies_to": "respondents_who_menstruate"},
        ],
        "phenotype": lca_phenotype_stub(),
        "wearable_platforms_supported": [p.value for p in WearablePlatform],
        "citation": (
            "Kosambiya RJ. Wearable-Augmented Perceived Stress Scale (WA-PSS), v3.0. "
            "NAMO Medical Education and Research Institute, Silvassa, 2026. "
            "Validation paper in submission to Indian Journal of Psychological Medicine."
        ),
    }


@app.get("/v1/sdk-mappings")
async def sdk_mappings():
    """
    Field-level mapping from WA-PSS biometric schema to each wearable platform's
    native SDK. Companion apps use this to read device data and POST to /v1/biometrics.
    """
    return {
        "purpose": "Map WA-PSS biometric fields to native wearable SDK field names",
        "license": "Open documentation",
        "mappings": SDK_FIELD_MAPPINGS,
        "integration_flow": [
            "1. Companion app obtains user permission via HealthKit (iOS) or Health Connect (Android)",
            "2. App reads wearable data using the platform SDK field names listed here",
            "3. App POSTs to /v1/biometrics with respondent_id and the mapped fields",
            "4. When the user completes WA-PSS via /v1/score with the same respondent_id, "
            "the latest biometric snapshot is auto-merged into the response",
            "5. Clinician views the longitudinal view via /v1/dashboard/{respondent_id}",
        ],
        "platforms_supported": [p.value for p in WearablePlatform],
    }


@app.get("/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "build": "full_v3_inclusive",
        "respondents_tracked": len(score_history),
        "biometric_snapshots_stored": sum(len(v) for v in biometric_store.values()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
