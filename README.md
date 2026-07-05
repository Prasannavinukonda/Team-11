# VisionGuard AI

Early detection of Diabetic Retinopathy using deep learning & computer vision — upload a retinal fundus photo, get a severity grade in seconds.

Built for the Final Year B.Tech AI & ML CRT 100-Day Project.

---

## About the ML model

VisionGuard AI ships with a **real trained checkpoint** integrated and
active by default (`MODEL_MODE=production`):

- **Architecture:** EfficientNet-B4 via [timm](https://github.com/huggingface/pytorch-image-models)
  (`timm.create_model("efficientnet_b4", num_classes=5)`) — *not* torchvision's
  EfficientNet-B4; the two have different internal layer names and are not
  interchangeable.
- **Checkpoint:** `backend/app/ml/weights/best_model.pth`, trained on the
  real [APTOS 2019 Blindness Detection](https://www.kaggle.com/competitions/aptos2019-blindness-detection)
  dataset at 380×380 resolution.
- **Current status: early checkpoint.** This run stopped at **epoch 2**
  with **validation F1 ≈ 0.58**. It produces real, non-random predictions,
  but accuracy is limited — this is a partially-trained model, not a
  finished one. The app surfaces this honestly: the dashboard and every
  screening result display the checkpoint's val F1 and epoch, and label
  results as provisional.

### Swapping in a better checkpoint later

The loader in `backend/app/ml/model.py` is designed so you never need to
touch code to upgrade the model:

1. Train a new checkpoint (more epochs, more data, etc.) with the same
   architecture: `timm.create_model("efficientnet_b4", num_classes=5)`.
2. Save it either way — both formats are auto-detected:
   ```python
   torch.save(model.state_dict(), "best_model.pth")
   # or
   torch.save({"model_state_dict": model.state_dict(), "val_f1": 0.81, "epoch": 25}, "best_model.pth")
   ```
3. Overwrite `backend/app/ml/weights/best_model.pth` with the new file
   and restart the backend. That's it.

If the new file is incompatible (wrong architecture, wrong number of
classes, corrupt file), the backend logs a specific, actionable error
explaining exactly what's wrong and falls back to demo mode rather than
silently loading garbage weights or crashing. See
`backend/tests/test_ml_model.py` for the exact scenarios this handles.

### Preprocessing — please verify this matches your training pipeline

The inference pipeline (`backend/app/ml/preprocessing.py`) applies:
center-crop to square → resize to 380×380 → CLAHE contrast enhancement on
the LAB lightness channel → ImageNet normalization. This is standard
practice for APTOS fundus photos, but **it was not derived from your
original training notebook** (which wasn't provided). If your training
pipeline used different preprocessing — a circular Ben Graham crop,
different CLAHE parameters, different normalization stats — predictions
will be quietly degraded by train/serve skew even though nothing errors.
Send over the training notebook and this can be matched exactly.

### Training a fresh model from scratch

`notebooks/train_efficientnet_aptos.ipynb` / `.py` train a fresh
timm EfficientNet-B4 on APTOS 2019 from scratch (Colab-ready, free GPU
tier), producing a checkpoint in the same format this app expects.

---

## Tech Stack

(matches the original pitch deck)

| Layer | Tech |
|---|---|
| Frontend | React.js, Tailwind CSS, Recharts |
| Backend | FastAPI (Python), REST API |
| Image processing | Pillow, OpenCV (CLAHE enhancement) |
| ML Model | EfficientNet-B4 (timm), PyTorch |
| Data & Training | APTOS 2019 dataset, Google Colab |
| Deployment | Docker, GitHub Actions CI |

Additions beyond the pitch deck, needed for a working product: SQLite/Postgres
database (SQLAlchemy), JWT authentication, and a REST API layer for
patients/screenings/dashboard.

---

## Project Structure

```
visionguard-ai/
├── backend/                   FastAPI app
│   ├── app/
│   │   ├── api/                Route handlers (auth, patients, screenings, dashboard)
│   │   ├── core/                Config + security (JWT, password hashing)
│   │   ├── db/                  SQLAlchemy session/engine
│   │   ├── ml/                  Model definition, CLAHE preprocessing, weights/
│   │   ├── models/              SQLAlchemy ORM models
│   │   ├── schemas/              Pydantic request/response schemas
│   │   └── services/            Inference + file storage business logic
│   ├── tests/                  Pytest suite
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                  React + Vite + Tailwind app
│   └── src/
│       ├── api/                 Axios client + endpoint wrappers
│       ├── context/             Auth context (JWT storage)
│       ├── components/          Layout, GradeBadge, ProtectedRoute
│       └── pages/                Login, Register, Dashboard, Patients, NewScreening
├── notebooks/                 Real APTOS 2019 training pipeline (notebook + script)
├── .github/workflows/ci.yml   Backend tests + frontend build + Docker build
└── docker-compose.yml         Full stack in two containers
```

---

## Quickstart (local dev, no Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Interactive API docs at
`http://localhost:8000/docs`.

The trained checkpoint (`backend/app/ml/weights/best_model.pth`, ~68MB)
is already included, so predictions work immediately — no download or
extra setup needed. If you ever delete it or set `MODEL_MODE=demo`, the
first backend startup will attempt to download ImageNet-pretrained
weights via timm, which needs internet access once.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api` to the
backend automatically (see `vite.config.js`).

### Run tests

```bash
cd backend && pytest -v
cd frontend && npm run build   # catches build/type errors
```

---

## Quickstart (Docker)

```bash
docker compose up --build
```

- Frontend: http://localhost
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

The included `best_model.pth` is baked into the backend image and copied
into the `backend_weights` volume on first run, so predictions work out
of the box. To swap in a newer checkpoint against a running stack:

```bash
docker cp new_best_model.pth visionguard-backend:/app/app/ml/weights/best_model.pth
docker restart visionguard-backend
```

Or simply replace the file in `backend/app/ml/weights/` and
`docker compose up --build` again.

---

## Using the app

1. Register an account (health worker / doctor / admin).
2. Add a patient.
3. Go to **New Screening**, pick the patient, upload a fundus photo (JPEG/PNG).
4. Get an instant severity grade (0–4), confidence score, class
   probabilities, and referral recommendation.
5. View aggregate stats and trends on the **Dashboard**.

---

## How It Works (matches the pitch deck)

1. **Upload** — health worker uploads a patient's retinal fundus photograph.
2. **Preprocess** — image is center-cropped, resized to 380×380, and
   enhanced with CLAHE (Contrast Limited Adaptive Histogram Equalization)
   on the LAB lightness channel — the standard trick for making
   microaneurysms and hemorrhages more visible in fundus photos.
3. **Classify** — EfficientNet-B4 predicts one of 5 DR grades: No DR /
   Mild / Moderate / Severe / Proliferative.
4. **Report** — instant result with severity label, confidence score, and
   referral recommendation (Grade ≥ 2 triggers a referral flag).

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account, returns JWT |
| POST | `/api/auth/login` | Login (OAuth2 form), returns JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/patients` | Add patient |
| GET | `/api/patients` | List patients (with latest grade) |
| GET | `/api/patients/{id}` | Patient detail |
| POST | `/api/screenings` | Upload image → run inference → save result |
| GET | `/api/screenings?patient_id=` | List screenings |
| GET | `/api/dashboard/stats` | Aggregate stats for charts |

Full interactive docs (Swagger UI) at `/docs` once the backend is running.

---

## Extending Toward the Final Version

- Swap SQLite → Postgres by changing `DATABASE_URL` (already supported;
  `psycopg2-binary` is in requirements.txt).
- Add Alembic migrations instead of `init_db()`'s `create_all` once the
  schema stabilizes.
- Move uploaded images to S3/GCS by editing only
  `app/services/storage_service.py` — the rest of the app doesn't know
  where files live.
- Deploy backend to Render or HuggingFace Spaces, frontend to
  Render/Vercel/Netlify, per the original pitch deck's deployment slide.
- Add per-facility multi-tenancy, patient search/filtering, PDF report
  export, and role-based access control (scaffolding for roles already
  exists in `UserRole`).

---

## 100-Day Plan Mapping (from the pitch deck)

| Phase | Days | What's already done here |
|---|---|---|
| 1. Research & Data | 1–25 | Dataset download script, CLAHE preprocessing pipeline ready |
| 2. Model Development | 26–50 | Training notebook/script with augmentation, class-weighted loss, QWK tracking — run it on real data |
| 3. Product Build | 51–75 | Full FastAPI backend + React frontend, done |
| 4. Polish & Demo | 76–100 | Swap in your trained weights, polish UI copy, record demo |
