from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.ml.model import CLASS_NAMES, DRClassifier
from app.models.patient import Patient
from app.models.screening import Screening
from app.schemas.screening import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
settings = get_settings()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: DbSession, current_user: CurrentUser):
    total_patients = db.query(Patient).count()
    screenings = db.query(Screening).order_by(Screening.created_at.asc()).all()
    total_screenings = len(screenings)

    grade_distribution = {label: 0 for label in CLASS_NAMES}
    referrals = 0
    by_day: dict[str, int] = defaultdict(int)

    for s in screenings:
        grade_distribution[CLASS_NAMES[s.grade]] += 1
        if s.referral_recommended:
            referrals += 1
        day_key = s.created_at.strftime("%Y-%m-%d")
        by_day[day_key] += 1

    referral_rate = round(referrals / total_screenings, 4) if total_screenings else 0.0
    screenings_over_time = [{"date": day, "count": count} for day, count in sorted(by_day.items())]

    classifier = DRClassifier.get_instance()
    return DashboardStats(
        total_patients=total_patients,
        total_screenings=total_screenings,
        grade_distribution=grade_distribution,
        referral_rate=referral_rate,
        screenings_over_time=screenings_over_time,
        model_mode=classifier.mode,
        model_val_f1=classifier.metadata.get("val_f1"),
        model_epoch=classifier.metadata.get("epoch"),
    )
