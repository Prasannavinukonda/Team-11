"""
EfficientNet-B4 (timm) classifier for Diabetic Retinopathy grading
(5 classes: No DR, Mild, Moderate, Severe, Proliferative).

Architecture note: this must match whatever library/variant the checkpoint
was trained with, since state_dict keys are architecture-specific. This
project's checkpoints are trained with:

    import timm
    model = timm.create_model("efficientnet_b4", pretrained=False, num_classes=5)

(NOT torchvision's efficientnet_b4 -- the two implementations use different
internal layer names, e.g. timm's "conv_stem"/"blocks.N.M"/"conv_head" vs.
torchvision's "features.N". A torchvision model will NOT load a timm
checkpoint, and vice versa.)

Two weight-loading modes, controlled by Settings.MODEL_MODE:

  "demo"       - Loads an ImageNet-pretrained backbone with a freshly
                 initialized classification head. The full upload ->
                 preprocess -> predict -> report pipeline runs end-to-end,
                 but grades are NOT clinically meaningful.

  "production" - Loads a fine-tuned checkpoint from MODEL_CHECKPOINT_PATH.
                 To upgrade to a newer checkpoint later, just overwrite
                 that file -- no code changes needed. The loader below
                 auto-detects the checkpoint format and validates
                 compatibility before use.

If the pretrained backbone can't be downloaded (e.g. an offline sandbox),
we fall back to a deterministically-seeded random init so the service
still boots and the API contract still works.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import timm
import torch
from torch import nn

from app.core.config import get_settings

logger = logging.getLogger("visionguard.ml")

MODEL_ARCH = "efficientnet_b4"
NUM_CLASSES = 5
CLASS_NAMES = ["No DR", "Mild", "Moderate", "Severe", "Proliferative"]
# Grades >= this value are flagged for specialist referral.
REFERRAL_THRESHOLD_GRADE = 2


class CheckpointIncompatibleError(Exception):
    """Raised when a checkpoint file can't be loaded into the current
    model architecture -- e.g. wrong backbone, wrong num_classes, or a
    file that isn't a recognizable checkpoint at all. The message is
    written to be directly actionable for whoever swapped in the file."""


def build_model(pretrained_backbone: bool = True) -> nn.Module:
    """Constructs a timm EfficientNet-B4 with a 5-class head."""
    try:
        model = timm.create_model(MODEL_ARCH, pretrained=pretrained_backbone, num_classes=NUM_CLASSES)
    except Exception as exc:  # no internet access to download ImageNet weights, etc.
        logger.warning("Falling back to un-pretrained %s backbone: %s", MODEL_ARCH, exc)
        model = timm.create_model(MODEL_ARCH, pretrained=False, num_classes=NUM_CLASSES)
    return model


def _extract_state_dict(checkpoint: Any) -> tuple[dict, dict]:
    """Handles both checkpoint formats people commonly save:

        torch.save(model.state_dict())
        torch.save({"model_state_dict": ..., "val_f1": ..., "epoch": ..., ...})
        torch.save({"state_dict": ..., ...})

    Returns (state_dict, metadata) where metadata holds any extra fields
    found alongside the weights (val_f1, epoch, training config, etc.)."""
    if not isinstance(checkpoint, dict):
        raise CheckpointIncompatibleError(
            f"Checkpoint file did not contain a dict (got {type(checkpoint).__name__}). "
            "Expected either a raw state_dict or a dict with a 'model_state_dict'/'state_dict' key."
        )

    for key in ("model_state_dict", "state_dict"):
        if key in checkpoint:
            state_dict = checkpoint[key]
            metadata = {k: v for k, v in checkpoint.items() if k != key}
            return state_dict, metadata

    # No wrapper key found -- treat the whole dict as a raw state_dict if
    # every value looks like a tensor.
    if checkpoint and all(isinstance(v, torch.Tensor) for v in checkpoint.values()):
        return checkpoint, {}

    raise CheckpointIncompatibleError(
        "Checkpoint dict has neither a 'model_state_dict'/'state_dict' key, nor does it look "
        f"like a raw state_dict (found top-level keys: {list(checkpoint.keys())[:10]}). "
        "Save your model with torch.save(model.state_dict(), path) or "
        "torch.save({'model_state_dict': model.state_dict(), ...}, path)."
    )


def load_checkpoint(model: nn.Module, checkpoint_path: Path, device: torch.device) -> dict:
    """Loads and validates a checkpoint into `model` in-place. Raises
    CheckpointIncompatibleError with a clear, actionable message on any
    mismatch instead of silently producing a garbage model. Returns
    whatever metadata (val_f1, epoch, config, ...) was saved alongside
    the weights, if any."""
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device)
    except Exception as exc:
        raise CheckpointIncompatibleError(f"Could not read checkpoint file '{checkpoint_path}': {exc}") from exc

    state_dict, metadata = _extract_state_dict(checkpoint)

    # Check classifier output size before touching load_state_dict, since
    # a class-count mismatch is the single most common integration error
    # and deserves a specific, obvious message.
    classifier_keys = [k for k in state_dict if k.endswith("classifier.weight")]
    if classifier_keys:
        ckpt_num_classes = state_dict[classifier_keys[0]].shape[0]
        if ckpt_num_classes != NUM_CLASSES:
            raise CheckpointIncompatibleError(
                f"Checkpoint's classifier outputs {ckpt_num_classes} classes, but this app expects "
                f"{NUM_CLASSES} (DR grades 0-4). This checkpoint was likely trained for a different task."
            )

    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing or unexpected:
        raise CheckpointIncompatibleError(
            "Checkpoint architecture does not match the expected model "
            f"({MODEL_ARCH} via timm, {NUM_CLASSES} classes).\n"
            f"  Missing keys ({len(missing)}): {missing[:5]}{' ...' if len(missing) > 5 else ''}\n"
            f"  Unexpected keys ({len(unexpected)}): {unexpected[:5]}{' ...' if len(unexpected) > 5 else ''}\n"
            "This usually means the checkpoint was trained with a different architecture/library "
            "(e.g. torchvision's efficientnet_b4 instead of timm's, or a different model size like "
            "B3/B5). Re-export the checkpoint with "
            f"timm.create_model('{MODEL_ARCH}', num_classes={NUM_CLASSES}), or update MODEL_ARCH here "
            "to match whatever architecture actually produced this file."
        )

    return metadata


class DRClassifier:
    """Thin singleton-style wrapper that owns the loaded model and exposes
    a simple `predict(tensor) -> (grade, probabilities)` API used by the
    inference service."""

    _instance: "DRClassifier | None" = None

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        torch.manual_seed(settings.MODEL_SEED)

        checkpoint_path = Path(settings.MODEL_CHECKPOINT_PATH)
        self.mode = settings.MODEL_MODE
        self.metadata: dict = {}
        # In production mode the checkpoint overwrites every weight anyway,
        # so skip the ImageNet download and save startup time/network calls.
        self.model = build_model(pretrained_backbone=(settings.MODEL_MODE != "production"))

        if settings.MODEL_MODE == "production":
            if checkpoint_path.exists():
                try:
                    self.metadata = load_checkpoint(self.model, checkpoint_path, self.device)
                    logger.info(
                        "Loaded production checkpoint from %s (metadata: %s)",
                        checkpoint_path,
                        {k: v for k, v in self.metadata.items() if k != "config"},
                    )
                except CheckpointIncompatibleError as exc:
                    logger.error(
                        "MODEL_MODE=production but checkpoint at %s is incompatible -- "
                        "falling back to demo weights.\n%s",
                        checkpoint_path,
                        exc,
                    )
                    self.model = build_model(pretrained_backbone=True)
                    self.mode = "demo"
            else:
                logger.warning(
                    "MODEL_MODE=production but no checkpoint found at %s -- "
                    "falling back to demo weights. Place a trained .pth file there.",
                    checkpoint_path,
                )
                self.model = build_model(pretrained_backbone=True)
                self.mode = "demo"

        self.model.to(self.device)
        self.model.eval()

    @classmethod
    def get_instance(cls) -> "DRClassifier":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Used by tests / hot-reload after swapping a checkpoint file."""
        cls._instance = None

    @torch.inference_mode()
    def predict(self, image_tensor: torch.Tensor) -> tuple[int, list[float]]:
        """image_tensor: shape (1, 3, H, W), already normalized."""
        image_tensor = image_tensor.to(self.device)
        logits = self.model(image_tensor)
        probabilities = torch.softmax(logits, dim=1).squeeze(0).cpu().tolist()
        grade = int(max(range(NUM_CLASSES), key=lambda i: probabilities[i]))
        return grade, probabilities
