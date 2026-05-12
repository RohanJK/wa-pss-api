"""
WA-PSS Scoring API v3.0
========================
Wearable-Augmented Perceived Stress Scale — inclusive scoring engine.

Design principle: gender identity, biological sex, and menstruation status
are captured as three independent fields. SQ12 (menstrual tracking concern)
is administered to anyone who indicates they menstruate, regardless of
gender identity.

Phase 1 build (Railway deployment): core scoring + inclusive profile.
Phase 2 additions: LCA classifier, biometric ingestion, longitudinal
dashboard, monetization router, Stripe integration.

© Dr. Rohan J. Kosambiya, 2026
Scale items: CC BY-NC 4.0
Classification algorithm: Proprietary (commercial license required)
Contact: rjkosambiya@gmail.com
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="WA-PSS Scoring API",
    version="3.0.0",
    description=(
        "Wearable-Augmented Perceived Stress Scale — inclusive, "
        "clinically grounded scoring engine. "
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


# ═══════════════════════════════════════════════════════════════════
# REQUEST MODEL
# ═══════════════════════════════════════════════════════════════════

class ScoreRequest(BaseModel):
    """
    WA-PSS scoring request.

    Profile fields:
    - gender_identity: required (9 options)
    - biological_sex: optional (used only for clinically relevant context)
    - menstruates: required boolean — controls SQ12 administration

    Items:
    - sq1 through sq11: required (0–4 Likert)
    - sq12: required ONLY if menstruates=True
    """

    # Profile
    respondent_id: Optional[str] = Field(
        None, description="Optional client-supplied identifier for longitudinal tracking"
    )
    age: int = Field(..., ge=13, le=100)
    gender_identity: GenderIdentity
    self_described_gender: Optional[str] = Field(
        None, description="Required if gender_identity=self_describe"
    )
    biological_sex: Optional[BiologicalSex] = None
    menstruates: bool = Field(
        ..., description="Independent of gender identity. Controls SQ12 administration."
    )

    # Items — PSS-derived (SQ1–SQ10), wearable-augmented (SQ11), conditional (SQ12)
    sq1: int = Field(..., ge=0, le=4, description="Upset by unexpected health-metric changes")
    sq2: int = Field(..., ge=0, le=4, description="Unable to control important health metrics")
    sq3: int = Field(..., ge=0, le=4, description="Nervous/stressed about health data")
    sq4: int = Field(..., ge=0, le=4, description="Confident handling health problems via device [R]")
    sq5: int = Field(..., ge=0, le=4, description="Things going well with health goals [R]")
    sq6: int = Field(..., ge=0, le=4, description="Could not cope with health demands/alerts")
    sq7: int = Field(..., ge=0, le=4, description="Able to control irritations from alerts [R]")
    sq8: int = Field(..., ge=0, le=4, description="On top of health-monitoring goals [R]")
    sq9: int = Field(..., ge=0, le=4, description="Angered by uncontrollable health metrics")
    sq10: int = Field(..., ge=0, le=4, description="Health goals piling up beyond management")
    sq11: int = Field(..., ge=0, le=4, description="I trust the health data on my wearable")
    sq12: Optional[int] = Field(
        None, ge=0, le=4,
        description="I worry about menstrual-cycle data on my device (required if menstruates=True)"
    )

    @model_validator(mode="after")
    def validate_conditional_items(self):
        if self.gender_identity == GenderIdentity.SELF_DESCRIBE and not self.self_described_gender:
            raise ValueError(
                "self_described_gender is required when gender_identity='self_describe'"
            )
        if self.menstruates and self.sq12 is None:
            raise ValueError(
                "sq12 is required when menstruates=True"
            )
        if not self.menstruates and self.sq12 is not None:
            raise ValueError(
                "sq12 must be omitted when menstruates=False"
            )
        return self


# ═══════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════

# PSS-10 reverse-scored item positions (1-indexed): 4, 5, 7, 8
REVERSE_ITEMS = {"sq4", "sq5", "sq7", "sq8"}


def reverse_score(value: int, max_value: int = 4) -> int:
    return max_value - value


def score_payload(req: ScoreRequest) -> dict:
    items = {
        "sq1": req.sq1, "sq2": req.sq2, "sq3": req.sq3, "sq4": req.sq4,
        "sq5": req.sq5, "sq6": req.sq6, "sq7": req.sq7, "sq8": req.sq8,
        "sq9": req.sq9, "sq10": req.sq10, "sq11": req.sq11,
    }
    if req.menstruates:
        items["sq12"] = req.sq12

    # Apply reverse scoring
    scored = {
        k: (reverse_score(v) if k in REVERSE_ITEMS else v)
        for k, v in items.items()
    }

    # PSS core (SQ1–SQ10)
    pss_core_keys = [f"sq{i}" for i in range(1, 11)]
    pss_total = sum(scored[k] for k in pss_core_keys)

    # Wearable-augmented total (includes SQ11, and SQ12 if administered)
    wa_total = sum(scored.values())

    # Severity bands — based on PSS-10 thresholds, rescaled for 11/12-item version
    n_items = len(scored)
    normalized = wa_total / (n_items * 4)  # 0–1 scale

    if normalized < 0.35:
        severity = SeverityBand.LOW
    elif normalized < 0.65:
        severity = SeverityBand.MODERATE
    else:
        severity = SeverityBand.HIGH

    return {
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
            "biological_sex": req.biological_sex.value if req.biological_sex else None,
            "menstruates": req.menstruates,
            "sq12_administered": req.menstruates,
        },
        "classification": {
            "lca_phenotype": "available_in_commercial_tier",
            "note": (
                "Four-class LCA-based stress phenotyping is part of the proprietary "
                "algorithm. Contact rjkosambiya@gmail.com for commercial licensing."
            ),
        },
        "licensing": {
            "scale_items": "CC BY-NC 4.0",
            "scoring_algorithm": "Proprietary — commercial license required for production use",
            "citation": (
                "Kosambiya RJ. Wearable-Augmented Perceived Stress Scale (WA-PSS), "
                "v3.0. 2026. Validation paper: Indian Journal of Psychological Medicine (in submission)."
            ),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "endpoints": {
            "score": "POST /v1/score",
            "scale": "GET /v1/scale",
            "health": "GET /v1/health",
            "docs": "GET /docs",
        },
        "license": {
            "scale": "CC BY-NC 4.0",
            "algorithm": "Proprietary",
        },
        "contact": "rjkosambiya@gmail.com",
    }


@app.post("/v1/score")
async def score(req: ScoreRequest):
    try:
        return score_payload(req)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/v1/scale")
async def scale():
    return {
        "instrument": "Wearable-Augmented Perceived Stress Scale (WA-PSS)",
        "version": "3.0.0",
        "license": "CC BY-NC 4.0 (items only — algorithm proprietary)",
        "design": {
            "profile_fields": {
                "gender_identity": "9 options including self-describe and prefer-not-to-say",
                "biological_sex": "Optional, 4 options. Used only when clinically relevant.",
                "menstruates": "Boolean. Controls SQ12 administration. Decoupled from gender identity.",
            },
            "core_items": "SQ1–SQ10 (PSS-derived, wearable-contextualized)",
            "augmented_item": "SQ11 (wearable trust)",
            "conditional_item": "SQ12 (menstrual-cycle data concern, administered if menstruates=True)",
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
        "citation": (
            "Kosambiya RJ. Wearable-Augmented Perceived Stress Scale (WA-PSS), v3.0. "
            "NAMO Medical Education and Research Institute, Silvassa, 2026. "
            "Validation paper in submission to Indian Journal of Psychological Medicine."
        ),
    }


@app.get("/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
