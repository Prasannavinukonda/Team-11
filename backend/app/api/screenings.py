import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.ml.model import DRClassifier
from app.models.patient import Patient
from app.models.screening import Screening
from app.schemas.screening import ScreeningOut
from app.services.inference_service import run_screening
from app.services.storage_service import save_upload

router = APIRouter(prefix="/screenings", tags=["screenings"])
settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}


@router.post("", response_model=ScreeningOut, status_code=status.HTTP_201_CREATED)
async def create_screening(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: int = Form(...),
    notes: str | None = Form(default=None),
    image: UploadFile = File(...),
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG or PNG fundus image")

    file_bytes = await image.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Image exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    try:
        result = run_screening(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process image: {exc}") from exc

    image_path = save_upload(file_bytes, image.filename or "upload.jpg")

    screening = Screening(
        patient_id=patient_id,
        image_path=image_path,
        grade=result.grade,
        grade_label=result.grade_label,
        confidence=result.confidence,
        class_probabilities=json.dumps(result.class_probabilities),
        referral_recommended=result.referral_recommended,
        model_mode=result.model_mode,
        notes=notes,
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)

    return _to_out(screening)


@router.get("", response_model=list[ScreeningOut])
def list_screenings(db: DbSession, current_user: CurrentUser, patient_id: int | None = None):
    query = db.query(Screening)
    if patient_id is not None:
        query = query.filter(Screening.patient_id == patient_id)
    screenings = query.order_by(Screening.created_at.desc()).all()
    return [_to_out(s) for s in screenings]


@router.get("/{screening_id}", response_model=ScreeningOut)
def get_screening(screening_id: int, db: DbSession, current_user: CurrentUser):
    screening = db.get(Screening, screening_id)
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")
    return _to_out(screening)


def _to_out(screening: Screening) -> ScreeningOut:
    metadata = DRClassifier.get_instance().metadata
    return ScreeningOut(
        id=screening.id,
        patient_id=screening.patient_id,
        grade=screening.grade,
        grade_label=screening.grade_label,
        confidence=screening.confidence,
        class_probabilities=json.loads(screening.class_probabilities),
        referral_recommended=screening.referral_recommended,
        model_mode=screening.model_mode,
        model_val_f1=metadata.get("val_f1"),
        model_epoch=metadata.get("epoch"),
        notes=screening.notes,
        created_at=screening.created_at,
    )
