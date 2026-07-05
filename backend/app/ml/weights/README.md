`best_model.pth` (already included) is a timm EfficientNet-B4 checkpoint
trained on APTOS 2019, currently at epoch 2 / val F1 ≈ 0.58 — a real but
early checkpoint, not a finished one.

To upgrade later: train a new checkpoint with
`timm.create_model("efficientnet_b4", num_classes=5)` (see
`notebooks/train_efficientnet_aptos.ipynb`), and overwrite this file.
No code changes needed -- `MODEL_MODE=production` in `backend/.env` is
already set, and the loader in `app/ml/model.py` auto-detects the
checkpoint format and validates compatibility on load.
