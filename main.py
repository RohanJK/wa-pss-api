"""
WA-PSS Scoring API v3.0
========================
Inclusive, clinically appropriate, production-ready.

Gender identity and biological sex are captured separately:
- Gender identity: Man, Woman, Non-binary, Prefer not to say, Self-describe
- Biological sex: Assigned female at birth / Assigned male at birth / Intersex / Prefer not to say
- Menstrual tracking (SQ12): Shown to anyone who indicates they menstruate
  (decoupled from gender identity — trans men, non-binary AFAB individuals menstruate too)

© Dr. Rohan J. Kosambiya, 2026
Scale: CC BY-NC 4.0 | Algorithm: Commercial License
"""

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import numpy as np

# ═══════════════════════════════════════
# APP
# ═══════════════════════════════════════

app = FastAPI(
    title="WA-PSS Scoring API",
    version="3.0.0",
    description=(
        "Wearable-Adapted Perceived Stress Scale — "
        "Inclusive, clinically validated scoring engine with wearable biomarker integration. "
        "Gender identity and biological sex captured separately. "
        "Menstrual tracking item (SQ12) offered based on self-reported menstruation status, "
        "not gender identity."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════
# AUTH
# ═══════════════════════════════════════

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Replace with database in production
API_KEYS = {
    "wapss_research_2026": {"tier": "research", "org": "demo"},
    "wapss_commercial_2026": {"tier": "commercial", "org": "demo"},
}

async def authenticate(key: str = Security(API_KEY_HEADER)):
    if not key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Missing API key",
                "help": "Include X-API-Key header. Contact rjkosambiya@gmail.com for access.",
            },
        )
    if key not in API_KEYS:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Invalid API key",
                "tiers": {
                    "research": "Free — basic scoring (total, severity, subscales)",
                    "commercial": "Licensed — classification, clinical flags, Temporal OS payload",
                },
                "contact": "rjkosambiya@gmail.com",
            },
        )
    return API_KEYS[key]

# ═══════════════════════════════════════
# STORAGE (replace with PostgreSQL + TimescaleDB in production)
# ═══════════════════════════════════════

biometric_store: Dict[str, list] = defaultdict(list)
score_history: Dict[str, list] = defaultdict(list)

# ═══════════════════════════════════════
# SCORING ENGINE (TRADE SECRET: centroids + normalization)
# ═══════════════════════════════════════

REVERSE_ITEMS = {4, 5, 7, 8}  # 1-indexed

FACTOR_LOADINGS = np.array([
    [0.64, 0.00, 0.00],  # SQ1
    [0.73, 0.00, 0.00],  # SQ2
    [0.72, 0.00, 0.00],  # SQ3
    [0.00, 0.88, 0.00],  # SQ4 (R)
    [0.00, 0.81, 0.00],  # SQ5 (R)
    [0.87, 0.00, 0.00],  # SQ6
    [0.00, 0.00, 0.66],  # SQ7 (R)
    [0.00, 0.36, 0.66],  # SQ8 (R)
    [0.82, 0.00, 0.00],  # SQ9
    [0.76, 0.00, 0.00],  # SQ10
])

# CALIBRATION: Replace with actual values from SPSS output
CENTROIDS = {
    "low_stress_casual": np.array([-0.52, -0.15, -0.30]),
    "proactive_balanced": np.array([0.10, 0.82, 0.65]),
    "high_stress_overmonitor": np.array([0.95, -0.45, -0.25]),
}

NORM_MEANS = np.array([2.1, 1.8, 1.9])
NORM_SDS = np.array([0.85, 0.90, 0.80])

PHENOTYPE_INFO = {
    "low_stress_casual": {
        "label": "Low-Stress Casual User",
        "risk": "LOW",
        "description": "Minimal distress, low device engagement.",
        "interventions": [
            "Gamified wellness challenges",
            "Preventive health nudges",
            "Meaningful tracking adoption support",
        ],
    },
    "proactive_balanced": {
        "label": "Proactive Balanced User",
        "risk": "NOMINAL",
        "description": "High confidence, emotional regulation, active engagement. Ideal wellness profile.",
        "interventions": [
            "Advanced coaching integration",
            "Goal escalation features",
            "Peer mentoring candidacy",
        ],
    },
    "high_stress_overmonitor": {
        "label": "High-Stress Over-Monitor",
        "risk": "HIGH",
        "description": "Elevated distress with compulsive monitoring. Intervention indicated.",
        "interventions": [
            "Tele-MANAS referral (14416)",
            "CBT-based alert modulation",
            "Monitoring frequency caps",
            "Clinician review recommended",
        ],
    },
    "unclassified": {
        "label": "Unclassified",
        "risk": "INDETERMINATE",
        "description": "Ambiguous profile. Additional assessment recommended.",
        "interventions": [
            "Retest in 2 weeks",
            "Clinical interview recommended",
        ],
    },
}

WEARABLE_PLATFORMS = {
    "apple_watch": {
        "name": "Apple Watch",
        "sync": "HealthKit Background Delivery",
        "os": "iOS",
        "sdk_fields": {
            "resting_heart_rate": "HKQuantityTypeIdentifierRestingHeartRate",
            "hrv": "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
            "steps": "HKQuantityTypeIdentifierStepCount",
            "sleep": "HKCategoryTypeIdentifierSleepAnalysis",
            "spo2": "HKQuantityTypeIdentifierOxygenSaturation",
            "respiratory_rate": "HKQuantityTypeIdentifierRespiratoryRate",
            "wrist_temperature": "HKQuantityTypeIdentifierAppleWalkingWristTemperature",
        },
    },
    "coros": {
        "name": "COROS",
        "sync": "COROS Training Hub API",
        "os": "iOS / Android",
        "sdk_fields": {
            "resting_heart_rate": "rest_hr",
            "hrv": "hrv",
            "steps": "daily_steps",
            "sleep_duration": "sleep_duration",
            "sleep_score": "sleep_score",
            "spo2": "spo2",
        },
    },
    "garmin": {
        "name": "Garmin",
        "sync": "Garmin Connect API / Health Connect",
        "os": "iOS / Android",
        "sdk_fields": {
            "resting_heart_rate": "restingHeartRate",
            "hrv": "hrvStatus",
            "steps": "totalSteps",
            "sleep": "sleepTimeSeconds",
            "sleep_score": "overallSleepScore",
            "spo2": "spo2",
            "respiratory_rate": "respirationRate",
            "stress": "stressLevel",
        },
    },
    "fitbit": {
        "name": "Fitbit / Google Pixel Watch",
        "sync": "Fitbit Web API / Health Connect",
        "os": "iOS / Android",
        "sdk_fields": {
            "resting_heart_rate": "resting_heart_rate",
            "steps": "steps",
            "sleep_score": "sleep_score",
            "spo2": "spo2",
            "stress": "stress_management_score",
        },
    },
    "samsung": {
        "name": "Samsung Galaxy Watch",
        "sync": "Samsung Health SDK / Health Connect",
        "os": "Android",
        "sdk_fields": {
            "heart_rate": "HeartRateRecord",
            "steps": "StepsRecord",
            "sleep": "SleepSessionRecord",
            "spo2": "OxygenSaturationRecord",
            "stress": "stress_score",
        },
    },
    "polar": {
        "name": "Polar",
        "sync": "Polar AccessLink API",
        "os": "iOS / Android",
        "sdk_fields": {
            "resting_heart_rate": "resting_hr",
            "hrv": "hrv",
            "steps": "steps",
            "sleep": "sleep",
        },
    },
    "noise": {"name": "Noise", "sync": "Manual entry", "os": "Android", "sdk_fields": {}},
    "boat": {"name": "boAt", "sync": "Manual entry", "os": "Android", "sdk_fields": {}},
    "fireboltt": {"name": "Fire-Boltt", "sync": "Manual entry", "os": "Android", "sdk_fields": {}},
    "other": {"name": "Other", "sync": "Manual entry", "os": "Any", "sdk_fields": {}},
}


def score_pss10(responses: list) -> dict:
    scored = [4 - v if (i + 1) in REVERSE_ITEMS else v for i, v in enumerate(responses)]
    total = sum(scored)
    severity = "low" if total <= 13 else ("moderate" if total <= 26 else "high")
    helplessness = sum(scored[i] for i in [0, 1, 2, 5, 8, 9])
    self_efficacy = sum(scored[i] for i in [3, 4, 6, 7])
    return {
        "total": total,
        "severity": severity,
        "helplessness": helplessness,
        "self_efficacy": self_efficacy,
    }


def compute_factor_scores(responses: list) -> np.ndarray:
    scored = np.array(
        [4 - v if (i + 1) in REVERSE_ITEMS else v for i, v in enumerate(responses)],
        dtype=float,
    )
    factors = []
    for f in range(3):
        weights = FACTOR_LOADINGS[:, f]
        mask = weights > 0
        if mask.any():
            factors.append(np.average(scored[mask], weights=weights[mask]))
        else:
            factors.append(0.0)
    return (np.array(factors) - NORM_MEANS) / NORM_SDS


def classify_phenotype(z_scores: np.ndarray) -> dict:
    distances = {k: np.linalg.norm(z_scores - c) for k, c in CENTROIDS.items()}
    neg_dists = np.array([-d for d in distances.values()])
    exp_vals = np.exp(neg_dists - neg_dists.max())
    probabilities = exp_vals / exp_vals.sum()
    prob_dict = dict(zip(distances.keys(), probabilities.tolist()))
    best = max(prob_dict, key=prob_dict.get)
    confidence = prob_dict[best]
    return {
        "phenotype": best if confidence >= 0.55 else "unclassified",
        "confidence": confidence,
        "probabilities": prob_dict,
    }


# ═══════════════════════════════════════
# MODELS — INCLUSIVE DESIGN
# ═══════════════════════════════════════

class GenderIdentity(str, Enum):
    """
    Gender identity is self-determined and independent of biological sex.
    Used for demographic analysis and gendered health disparities research.
    """
    man = "man"
    woman = "woman"
    non_binary = "non_binary"
    genderqueer = "genderqueer"
    genderfluid = "genderfluid"
    agender = "agender"
    two_spirit = "two_spirit"
    prefer_not_to_say = "prefer_not_to_say"
    self_describe = "self_describe"


class BiologicalSex(str, Enum):
    """
    Sex assigned at birth. Used only when clinically relevant
    (e.g., pharmacogenomic dosing, hormone-linked biomarker interpretation).
    """
    assigned_female = "assigned_female_at_birth"
    assigned_male = "assigned_male_at_birth"
    intersex = "intersex"
    prefer_not_to_say = "prefer_not_to_say"


class BiometricPush(BaseModel):
    """Push wearable data from native app (iOS/Android)."""
    respondent_id: str = Field(..., description="Unique respondent identifier")
    platform: str = Field(..., description="Wearable platform (e.g., 'coros', 'apple_watch')")
    timestamp: Optional[str] = Field(None, description="ISO 8601. Defaults to server time")
    readings: dict = Field(
        ...,
        description="Key-value biometric readings",
        examples=[{
            "resting_heart_rate": 68,
            "hrv": 42,
            "steps": 8500,
            "sleep_hours": 6.5,
            "spo2": 97,
        }],
    )


class ScoreRequest(BaseModel):
    """
    WA-PSS scoring request.
    
    INCLUSIVE DESIGN:
    - gender_identity: How the respondent identifies (demographic/research)
    - biological_sex: Sex assigned at birth (clinical relevance only)
    - menstruates: Whether the respondent currently menstruates
      → This determines whether SQ12 is administered
      → Decoupled from both gender identity and biological sex
      → Trans men, non-binary AFAB individuals, and others who menstruate see SQ12
      → Post-menopausal women, trans women, and others who don't menstruate skip SQ12
    """

    # ── Respondent ID (for longitudinal tracking + biometric auto-merge) ──
    respondent_id: Optional[str] = Field(
        None, description="If provided, auto-pulls stored wearable biometrics"
    )

    # ── Inclusive Demographics ──
    gender_identity: GenderIdentity = Field(
        ..., description="Self-identified gender"
    )
    gender_self_description: Optional[str] = Field(
        None, description="Free text if gender_identity is 'self_describe'"
    )
    biological_sex: Optional[BiologicalSex] = Field(
        None, description="Sex assigned at birth (optional, clinical use only)"
    )
    menstruates: bool = Field(
        ...,
        description=(
            "Does the respondent currently menstruate? "
            "Determines whether SQ12 (menstrual tracking concern) is administered. "
            "This is independent of gender identity."
        ),
    )
    age: Optional[int] = Field(None, ge=18, le=65)
    designation: Optional[str] = Field(None, description="Professional role")
    city: Optional[str] = None

    # ── Wearable Context ──
    device_brand: Optional[str] = Field(None, description="e.g., 'coros', 'apple_watch'")
    wearable_duration_months: Optional[int] = Field(None, ge=0)

    # ── Manual Biometrics (fallback if no stored data) ──
    heart_rate: Optional[float] = Field(None, ge=30, le=220, description="Resting HR (bpm)")
    hrv: Optional[float] = Field(None, ge=1, le=300, description="HRV RMSSD (ms)")
    steps: Optional[float] = Field(None, ge=0, description="Daily average steps")
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Avg sleep (hours)")
    sleep_score: Optional[float] = Field(None, ge=0, le=100, description="Sleep quality /100")
    spo2: Optional[float] = Field(None, ge=70, le=100, description="SpO2 %")
    respiratory_rate: Optional[float] = Field(None, ge=4, le=60, description="Breaths/min")
    skin_temp: Optional[float] = Field(None, ge=25, le=45, description="Skin temp °C")
    stress_score: Optional[float] = Field(None, ge=0, le=100, description="Device stress /100")
    active_minutes: Optional[float] = Field(None, ge=0, description="Daily active minutes")

    # ── PSS-10 Core Items (ALWAYS required) ──
    sq1: int = Field(..., ge=0, le=4, description="Upset by unexpected health parameter changes")
    sq2: int = Field(..., ge=0, le=4, description="Unable to control important health metrics")
    sq3: int = Field(..., ge=0, le=4, description="Nervous and stressed about health data")
    sq4: int = Field(..., ge=0, le=4, description="Confident handling health problems via device (R)")
    sq5: int = Field(..., ge=0, le=4, description="Things going well with health goals (R)")
    sq6: int = Field(..., ge=0, le=4, description="Could not cope with health demands and alerts")
    sq7: int = Field(..., ge=0, le=4, description="Able to control irritations from alerts (R)")
    sq8: int = Field(..., ge=0, le=4, description="On top of health monitoring goals (R)")
    sq9: int = Field(..., ge=0, le=4, description="Angered by uncontrollable health metrics")
    sq10: int = Field(..., ge=0, le=4, description="Health goals piling up beyond management")

    # ── Additional WA-PSS Items ──
    sq11: Optional[int] = Field(None, ge=0, le=4, description="Trust in smartwatch health data")
    sq12: Optional[int] = Field(
        None, ge=0, le=4,
        description="Concern about menstrual cycle data — ONLY if menstruates=true",
    )

    @model_validator(mode="after")
    def validate_menstrual_item(self):
        if not self.menstruates and self.sq12 is not None:
            raise ValueError(
                "SQ12 (menstrual tracking concern) should only be provided when "
                "menstruates=true. This item is not applicable for respondents "
                "who do not currently menstruate."
            )
        if self.gender_identity == GenderIdentity.self_describe and not self.gender_self_description:
            raise ValueError(
                "gender_self_description is required when gender_identity is 'self_describe'"
            )
        return self


# ═══════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════

@app.get("/")
async def root():
    return {
        "service": "WA-PSS Scoring API",
        "version": "3.0.0",
        "description": (
            "Wearable-Adapted Perceived Stress Scale — Inclusive, clinically validated "
            "scoring engine with wearable biomarker integration and digital phenotype classification."
        ),
        "inclusive_design": {
            "gender_identity": "Self-determined, 9 options including self-describe",
            "biological_sex": "Optional, for clinical use only",
            "menstrual_item": (
                "SQ12 is administered based on self-reported menstruation status, "
                "NOT gender identity. Trans men, non-binary AFAB individuals, "
                "and all people who menstruate are included."
            ),
        },
        "license": {
            "scale_items": "CC BY-NC 4.0 (open for research)",
            "classification_algorithm": "Commercial license required",
            "trade_secret": "Cluster centroids, normalization parameters, decision thresholds",
        },
        "pricing": {
            "research": "Free (basic scoring: total, severity, subscales)",
            "commercial": "INR 2-5 per API call or annual subscription",
            "contact": "rjkosambiya@gmail.com",
        },
        "citation": (
            "Kosambiya RJ et al. WA-PSS: Development and Psychometric Validation of the "
            "Wearable-Adapted Perceived Stress Scale. Indian Journal of Psychological Medicine. 2026."
        ),
        "endpoints": {
            "POST /v1/score": "Score WA-PSS + classify phenotype + auto-merge wearable data",
            "POST /v1/biometrics": "Push live wearable data from native app",
            "GET /v1/dashboard/{respondent_id}": "Clinician longitudinal trajectory view",
            "GET /v1/scale": "Scale items with inclusive administration guide (CC BY-NC 4.0)",
            "GET /v1/platforms": "Supported wearable platforms with SDK field mapping",
            "GET /v1/health": "Service health check",
        },
        "documentation": "/docs",
    }


@app.post("/v1/biometrics")
async def push_biometrics(data: BiometricPush, cred: dict = Depends(authenticate)):
    ts = data.timestamp or datetime.now(timezone.utc).isoformat()
    platform = WEARABLE_PLATFORMS.get(data.platform)
    if not platform:
        raise HTTPException(
            400,
            detail={
                "error": f"Unknown platform: {data.platform}",
                "supported": list(WEARABLE_PLATFORMS.keys()),
                "help": "GET /v1/platforms for full list with SDK field mapping",
            },
        )

    biometric_store[data.respondent_id].append({
        "timestamp": ts,
        "platform": data.platform,
        "readings": data.readings,
    })

    # Retain 90 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    biometric_store[data.respondent_id] = [
        e for e in biometric_store[data.respondent_id] if e["timestamp"] >= cutoff
    ]

    return {
        "status": "stored",
        "respondent_id": data.respondent_id,
        "platform": platform["name"],
        "readings_received": len(data.readings),
        "total_stored": len(biometric_store[data.respondent_id]),
        "next_step": "POST /v1/score with the same respondent_id to auto-merge biometrics",
    }


@app.post("/v1/score")
async def score_wapss(req: ScoreRequest, cred: dict = Depends(authenticate)):
    tier = cred["tier"]
    responses = [req.sq1, req.sq2, req.sq3, req.sq4, req.sq5,
                 req.sq6, req.sq7, req.sq8, req.sq9, req.sq10]

    pss = score_pss10(responses)

    # Resolve biometrics: auto-merge from store or manual entry
    biometrics = {}
    bio_source = "none"

    if req.respondent_id and req.respondent_id in biometric_store:
        stored = biometric_store[req.respondent_id]
        if stored:
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            recent = [e for e in stored if e["timestamp"] >= week_ago]
            if len(recent) >= 3:
                avg = {}
                for entry in recent:
                    for k, v in entry["readings"].items():
                        if isinstance(v, (int, float)):
                            avg.setdefault(k, []).append(v)
                biometrics = {k: round(sum(v) / len(v), 2) for k, v in avg.items()}
                bio_source = f"7-day average ({len(recent)} syncs)"
            else:
                biometrics = stored[-1]["readings"]
                bio_source = f"latest sync ({stored[-1]['platform']})"

    if not biometrics:
        for field in ["heart_rate", "hrv", "steps", "sleep_hours", "sleep_score",
                      "spo2", "respiratory_rate", "skin_temp", "stress_score", "active_minutes"]:
            val = getattr(req, field)
            if val is not None:
                biometrics[field] = val
        if biometrics:
            bio_source = "manual_entry"

    # Determine item count
    items_administered = 10
    if req.sq11 is not None:
        items_administered += 1
    if req.menstruates and req.sq12 is not None:
        items_administered += 1

    # Build response
    gender_display = (
        req.gender_self_description
        if req.gender_identity == GenderIdentity.self_describe
        else req.gender_identity.value.replace("_", " ").title()
    )

    result = {
        "meta": {
            "api_version": "3.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tier": tier,
            "respondent_id": req.respondent_id,
        },
        "respondent": {
            "gender_identity": req.gender_identity.value,
            "gender_display": gender_display,
            "biological_sex": req.biological_sex.value if req.biological_sex else None,
            "menstruates": req.menstruates,
            "age": req.age,
            "items_administered": items_administered,
        },
        "scoring": {
            "pss_total": pss["total"],
            "severity": pss["severity"],
            "severity_range": {"low": "0-13", "moderate": "14-26", "high": "27-40"},
            "subscales": {
                "perceived_helplessness": {"score": pss["helplessness"], "max": 24},
                "perceived_self_efficacy": {"score": pss["self_efficacy"], "max": 16},
            },
            "additional_items": {
                "sq11_device_trust": req.sq11,
                **({"sq12_menstrual_concern": req.sq12} if req.menstruates else {}),
            },
        },
        "biometrics": {
            "source": bio_source,
            "data": biometrics,
        },
    }

    # Commercial tier: classification + flags + Temporal OS
    if tier == "commercial":
        z = compute_factor_scores(responses)
        cls = classify_phenotype(z)
        phenotype = cls["phenotype"]
        meta = PHENOTYPE_INFO[phenotype]

        adapt = req.wearable_duration_months is not None and req.wearable_duration_months <= 3
        elevated_distress = float(z[0]) > 1.5
        low_efficacy = float(z[1]) < -1.0
        tele_manas = pss["severity"] == "high" or (elevated_distress and low_efficacy)

        # Gender-informed risk: based on biological sex if provided, not gender identity
        bio_female_elevated = (
            req.biological_sex == BiologicalSex.assigned_female
            and elevated_distress
        )

        result["factor_analysis"] = {
            "method": "EFA (Principal Axis Factoring, Varimax rotation)",
            "total_variance_explained": "60.2%",
            "factors": {
                "emotional_distress": {
                    "z_score": round(float(z[0]), 4),
                    "items": ["SQ1", "SQ2", "SQ3", "SQ6", "SQ9", "SQ10"],
                    "variance": "34.83%",
                },
                "self_efficacy": {
                    "z_score": round(float(z[1]), 4),
                    "items": ["SQ4", "SQ5"],
                    "variance": "15.93%",
                },
                "emotional_control": {
                    "z_score": round(float(z[2]), 4),
                    "items": ["SQ7", "SQ8"],
                    "variance": "9.41%",
                },
            },
        }

        result["classification"] = {
            "method": "LCA 3-class solution (softmax over Euclidean distance)",
            "phenotype": phenotype,
            "label": meta["label"],
            "description": meta["description"],
            "confidence": round(cls["confidence"], 4),
            "risk_level": meta["risk"],
            "class_probabilities": {
                k: round(v, 4) for k, v in cls["probabilities"].items()
            },
        }

        result["clinical_flags"] = {
            "elevated_distress": elevated_distress,
            "low_self_efficacy": low_efficacy,
            "afab_elevated_distress": bio_female_elevated,
            "adaptation_phase": adapt,
            "tele_manas_referral": tele_manas,
            "tele_manas_helpline": "14416" if tele_manas else None,
        }

        result["interventions"] = meta["interventions"]

        result["temporal_os"] = {
            "layer": 1,
            "module": "digital_phenotyping",
            "phenotype_id": phenotype,
            "factor_vector": [round(float(x), 4) for x in z],
            "biometric_context": biometrics,
            "biometric_source": bio_source,
            "integration_ready": True,
        }

        # Store for longitudinal tracking
        if req.respondent_id:
            score_history[req.respondent_id].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pss_total": pss["total"],
                "severity": pss["severity"],
                "phenotype": phenotype,
                "confidence": round(cls["confidence"], 4),
                "factors": [round(float(x), 4) for x in z],
                "tele_manas": tele_manas,
            })

    return result


@app.get("/v1/dashboard/{respondent_id}")
async def dashboard(respondent_id: str, cred: dict = Depends(authenticate)):
    if cred["tier"] != "commercial":
        raise HTTPException(403, detail="Dashboard requires commercial tier API key")

    scores = score_history.get(respondent_id, [])
    bios = biometric_store.get(respondent_id, [])

    if not scores:
        return {
            "respondent_id": respondent_id,
            "status": "no_assessments",
            "message": "No WA-PSS assessments recorded for this respondent.",
        }

    latest = scores[-1]

    transitions = []
    for i in range(1, len(scores)):
        if scores[i]["phenotype"] != scores[i - 1]["phenotype"]:
            transitions.append({
                "from": scores[i - 1]["phenotype"],
                "to": scores[i]["phenotype"],
                "timestamp": scores[i]["timestamp"],
            })

    return {
        "respondent_id": respondent_id,
        "total_assessments": len(scores),
        "total_biometric_syncs": len(bios),
        "current": {
            "phenotype": latest["phenotype"],
            "label": PHENOTYPE_INFO[latest["phenotype"]]["label"],
            "pss_total": latest["pss_total"],
            "severity": latest["severity"],
            "confidence": latest["confidence"],
            "factors": {
                "emotional_distress": latest["factors"][0],
                "self_efficacy": latest["factors"][1],
                "emotional_control": latest["factors"][2],
            },
            "tele_manas_flagged": latest["tele_manas"],
        },
        "trajectory": [
            {"timestamp": s["timestamp"], "pss": s["pss_total"], "phenotype": s["phenotype"]}
            for s in scores
        ],
        "transitions": transitions,
        "trend": (
            "improving" if len(scores) >= 2 and scores[-1]["pss_total"] < scores[0]["pss_total"]
            else "worsening" if len(scores) >= 2 and scores[-1]["pss_total"] > scores[0]["pss_total"]
            else "stable"
        ),
    }


@app.get("/v1/scale")
async def scale_items():
    """
    Returns WA-PSS items with inclusive administration guide.
    Licensed under CC BY-NC 4.0 for research use.
    """
    return {
        "instrument": "WA-PSS (Wearable-Adapted Perceived Stress Scale)",
        "version": "3.0.0",
        "license": "CC BY-NC 4.0",
        "citation_required": True,
        "base_instrument": "PSS-10 (Cohen, Kamarck & Mermelstein, 1983)",
        "inclusive_administration_guide": {
            "principle": (
                "Menstrual tracking item (SQ12) is administered based on self-reported "
                "menstruation status, not gender identity or sex assigned at birth. "
                "This ensures clinical accuracy and gender inclusivity."
            ),
            "ask_the_respondent": "Do you currently menstruate?",
            "if_yes": "Administer SQ1-SQ12 (12 items)",
            "if_no": "Administer SQ1-SQ11 (11 items)",
            "examples": {
                "cisgender_woman_premenopausal": "menstruates=true → SQ1-SQ12",
                "cisgender_woman_postmenopausal": "menstruates=false → SQ1-SQ11",
                "trans_man_menstruating": "menstruates=true → SQ1-SQ12",
                "trans_man_on_testosterone": "menstruates=false → SQ1-SQ11",
                "non_binary_afab_menstruating": "menstruates=true → SQ1-SQ12",
                "cisgender_man": "menstruates=false → SQ1-SQ11",
                "trans_woman": "menstruates=false → SQ1-SQ11",
            },
        },
        "response_options": {
            0: "Never",
            1: "Almost Never",
            2: "Sometimes",
            3: "Fairly Often",
            4: "Very Often",
        },
        "reverse_scored_items": ["SQ4", "SQ5", "SQ7", "SQ8"],
        "items": {
            "core_pss10": [
                {"id": "SQ1", "text": "In the last month, how often have you been upset because of unexpected changes in your health parameters on your smartwatch?", "factor": "emotional_distress", "reverse": False},
                {"id": "SQ2", "text": "In the last month, how often have you felt that you were unable to control the important health metrics in your life?", "factor": "emotional_distress", "reverse": False},
                {"id": "SQ3", "text": "In the last month, how often have you felt nervous and stressed about your health data?", "factor": "emotional_distress", "reverse": False},
                {"id": "SQ4", "text": "In the last month, how often have you felt confident about your ability to handle your health problems based on smartwatch data?", "factor": "self_efficacy", "reverse": True},
                {"id": "SQ5", "text": "In the last month, how often have you felt that things were going your way in managing health goals through your device?", "factor": "self_efficacy", "reverse": True},
                {"id": "SQ6", "text": "In the last month, how often have you found that you could not cope with all the health-related demands and alerts?", "factor": "emotional_distress", "reverse": False},
                {"id": "SQ7", "text": "In the last month, how often have you been able to control irritations triggered by health monitoring alerts?", "factor": "emotional_control", "reverse": True},
                {"id": "SQ8", "text": "In the last month, how often have you felt that you were on top of your health monitoring goals?", "factor": "emotional_control", "reverse": True},
                {"id": "SQ9", "text": "In the last month, how often have you been angered because of health metrics that were outside of your control?", "factor": "emotional_distress", "reverse": False},
                {"id": "SQ10", "text": "In the last month, how often have you felt that health goals and concerns were piling up so high that you could not manage them?", "factor": "emotional_distress", "reverse": False},
            ],
            "additional": [
                {"id": "SQ11", "text": "I trust the health data displayed on my smartwatch.", "administered_to": "all_respondents"},
                {"id": "SQ12", "text": "I worry about my menstrual cycle data shown by my device.", "administered_to": "respondents_who_menstruate_only"},
            ],
        },
    }


@app.get("/v1/platforms")
async def platforms():
    return {
        "supported_platforms": {
            k: {
                "name": v["name"],
                "sync_method": v["sync"],
                "compatible_os": v["os"],
                "sdk_fields": v["sdk_fields"],
            }
            for k, v in WEARABLE_PLATFORMS.items()
        },
        "integration_flow": [
            "1. User installs companion app (iOS/Android)",
            "2. App requests HealthKit (iOS) or Health Connect (Android) permissions",
            "3. App reads wearable data using platform-specific SDK fields listed above",
            "4. App pushes readings to POST /v1/biometrics with respondent_id",
            "5. When user completes WA-PSS, app sends POST /v1/score with same respondent_id",
            "6. API auto-merges latest 7-day biometric average into scoring response",
            "7. Clinician views GET /v1/dashboard/{respondent_id} for longitudinal trajectory",
        ],
    }


@app.get("/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "respondents_tracked": len(score_history),
        "biometric_syncs_stored": sum(len(v) for v in biometric_store.values()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
