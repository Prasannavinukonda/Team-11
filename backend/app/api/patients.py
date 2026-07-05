from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientDetail, PatientOut

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: DbSession, current_user: CurrentUser):
    patient = Patient(**payload.model_dump(), created_by_id=current_user.id)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=list[PatientDetail])
def list_patients(db: DbSession, current_user: CurrentUser):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    results = []
    for p in patients:
        latest_grade = p.screenings[0].grade if p.screenings else None
        results.append(
            PatientDetail(
                **PatientOut.model_validate(p).model_dump(),
                screening_count=len(p.screenings),
                latest_grade=latest_grade,
            )
        )
    return results


@router.get("/{patient_id}", response_model=PatientDetail)
def get_patient(patient_id: int, db: DbSession, current_user: CurrentUser):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    latest_grade = patient.screenings[0].grade if patient.screenings else None
    return PatientDetail(
        **PatientOut.model_validate(patient).model_dump(),
        screening_count=len(patient.screenings),
        latest_grade=latest_grade,
    )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, db: DbSession, current_user: CurrentUser):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
