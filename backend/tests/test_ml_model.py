"""
Unit tests for app.ml.model's checkpoint loading logic: format detection
(wrapped dict vs raw state_dict), class-count validation, and clear
failure on incompatible/corrupt files.
"""
import tempfile
from pathlib import Path

import pytest
import torch

from app.ml.model import (
    CheckpointIncompatibleError,
    NUM_CLASSES,
    build_model,
    load_checkpoint,
)


def _save_tmp(obj) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".pth", delete=False)
    torch.save(obj, f.name)
    return Path(f.name)


def test_loads_wrapped_checkpoint_with_model_state_dict_key():
    reference = build_model(pretrained_backbone=False)
    path = _save_tmp({"model_state_dict": reference.state_dict(), "val_f1": 0.9, "epoch": 12})

    model = build_model(pretrained_backbone=False)
    metadata = load_checkpoint(model, path, torch.device("cpu"))

    assert metadata["val_f1"] == 0.9
    assert metadata["epoch"] == 12


def test_loads_wrapped_checkpoint_with_state_dict_key():
    reference = build_model(pretrained_backbone=False)
    path = _save_tmp({"state_dict": reference.state_dict()})

    model = build_model(pretrained_backbone=False)
    metadata = load_checkpoint(model, path, torch.device("cpu"))
    assert metadata == {}


def test_loads_raw_state_dict_without_wrapper():
    reference = build_model(pretrained_backbone=False)
    path = _save_tmp(reference.state_dict())

    model = build_model(pretrained_backbone=False)
    metadata = load_checkpoint(model, path, torch.device("cpu"))
    assert metadata == {}


def test_rejects_wrong_num_classes_with_clear_message():
    bad = {
        "model_state_dict": {
            "classifier.weight": torch.randn(10, 1792),
            "classifier.bias": torch.randn(10),
        }
    }
    path = _save_tmp(bad)
    model = build_model(pretrained_backbone=False)

    with pytest.raises(CheckpointIncompatibleError, match="10 classes"):
        load_checkpoint(model, path, torch.device("cpu"))


def test_rejects_non_checkpoint_dict_with_clear_message():
    path = _save_tmp({"foo": "bar", "baz": 123})
    model = build_model(pretrained_backbone=False)

    with pytest.raises(CheckpointIncompatibleError, match="model_state_dict"):
        load_checkpoint(model, path, torch.device("cpu"))


def test_rejects_architecture_mismatch_with_clear_message():
    # A state dict with plausible-looking but wrong key names (as if from
    # a different architecture) should fail with a descriptive error
    # rather than loading silently-wrong weights.
    fake_other_arch = {"model_state_dict": {"totally.different.layer.name": torch.randn(3, 3)}}
    path = _save_tmp(fake_other_arch)
    model = build_model(pretrained_backbone=False)

    with pytest.raises(CheckpointIncompatibleError, match="does not match"):
        load_checkpoint(model, path, torch.device("cpu"))


def test_model_output_shape():
    model = build_model(pretrained_backbone=False)
    model.eval()
    with torch.no_grad():
        out = model(torch.randn(1, 3, 380, 380))
    assert out.shape == (1, NUM_CLASSES)
