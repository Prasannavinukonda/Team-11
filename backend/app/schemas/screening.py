from datetime import datetime

from pydantic import BaseModel


class ScreeningOut(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    patient_id: int
    grade: int
    grade_label: str
    confidence: float
    class_probabilities: list[float]
    referral_recommended: bool
    model_mode: str
    model_val_f1: float | None = None
    model_epoch: int | None = None
    notes: str | None = None
    created_at: datetime


class DashboardStats(BaseModel):
    model_config = {"protected_namespaces": ()}

    total_patients: int
    total_screenings: int
    grade_distribution: dict[str, int]
    referral_rate: float
    screenings_over_time: list[dict]
    model_mode: str
    model_val_f1: float | None = None
    model_epoch: int | None = None
