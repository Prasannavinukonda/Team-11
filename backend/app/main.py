import logging

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, dashboard, patients, screenings
from app.core.config import get_settings
from app.db.session import init_db
from app.ml.model import DRClassifier

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Load the model once here, at process startup, rather than lazily on
    # the first request -- avoids a slow first prediction and lets startup
    # fail loudly if the checkpoint is broken, instead of failing on a
    # user's first upload.
    classifier = DRClassifier.get_instance()
    logging.getLogger("visionguard.startup").info(
        "Model ready: mode=%s device=%s", classifier.mode, classifier.device
    )
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Early detection of Diabetic Retinopathy using deep learning & computer vision.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health_check():
    classifier = DRClassifier.get_instance()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "model_mode": classifier.mode,
        "model_metadata": {k: v for k, v in classifier.metadata.items() if k != "config"},
    }


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(patients.router, prefix=settings.API_V1_PREFIX)
app.include_router(screenings.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
