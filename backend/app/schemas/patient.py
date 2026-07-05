from datetime import datetime

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    age: int = Field(ge=0, le=120)
    gender: str
    contact: str | None = None
    diabetes_duration_years: int | None = Field(default=None, ge=0, le=100)


class PatientOut(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    contact: str | None = None
    diabetes_duration_years: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientDetail(PatientOut):
    screening_count: int = 0
    latest_grade: int | None = None
