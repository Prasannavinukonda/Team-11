"""Business logic for running a screening: preprocess -> predict -> package
the result. Kept separate from the API layer so it's easy to unit test or
reuse (e.g. from a batch/CLI script)."""
from __future__ import annotations

from app.core.config import get_settings
from app.ml.model import CLASS_NAMES, REFERRAL_THRESHOLD_GRADE, DRClassifier
from app.ml.preprocessing import preprocess_image

settings = get_settings()


class ScreeningResult:
    def __init__(self, grade: int, probabilities: list[float], model_mode: str):
        self.grade = grade
        self.grade_label = CLASS_NAMES[grade]
        self.confidence = round(probabilities[grade], 4)
        self.class_probabilities = [round(p, 4) for p in probabilities]
        self.referral_recommended = grade >= REFERRAL_THRESHOLD_GRADE
        self.model_mode = model_mode


def run_screening(file_bytes: bytes) -> ScreeningResult:
    classifier = DRClassifier.get_instance()
    tensor = preprocess_image(file_bytes, img_size=settings.MODEL_IMG_SIZE)
    grade, probabilities = classifier.predict(tensor)
    return ScreeningResult(grade=grade, probabilities=probabilities, model_mode=classifier.mode)
