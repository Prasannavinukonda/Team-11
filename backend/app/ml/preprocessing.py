"""
Retinal fundus image preprocessing.

Pipeline: decode -> center-crop to square -> resize -> CLAHE contrast
enhancement (applied on the green channel + LAB lightness, which is the
standard trick for fundus photos since the green channel carries the most
vascular detail) -> normalize to ImageNet mean/std -> tensor.
"""
from __future__ import annotations

import io

import cv2
import numpy as np
import torch
from PIL import Image

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _apply_clahe(image_rgb: np.ndarray) -> np.ndarray:
    """Contrast Limited Adaptive Histogram Equalization on the L channel
    of LAB color space - improves visibility of microaneurysms and
    hemorrhages without blowing out bright regions like the optic disc."""
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    lab = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def _center_crop_square(image_rgb: np.ndarray) -> np.ndarray:
    h, w = image_rgb.shape[:2]
    side = min(h, w)
    top = (h - side) // 2
    left = (w - side) // 2
    return image_rgb[top : top + side, left : left + side]


def preprocess_image(file_bytes: bytes, img_size: int = 380) -> torch.Tensor:
    """Raw uploaded file bytes -> normalized (1, 3, H, W) float tensor
    ready for the model."""
    pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    image_rgb = np.array(pil_image)

    image_rgb = _center_crop_square(image_rgb)
    image_rgb = cv2.resize(image_rgb, (img_size, img_size), interpolation=cv2.INTER_AREA)
    image_rgb = _apply_clahe(image_rgb)

    image_float = image_rgb.astype(np.float32) / 255.0
    image_float = (image_float - IMAGENET_MEAN) / IMAGENET_STD

    tensor = torch.from_numpy(image_float).permute(2, 0, 1).unsqueeze(0).float()
    return tensor


def preprocessed_preview(file_bytes: bytes, img_size: int = 380) -> bytes:
    """Returns a JPEG-encoded preview of the CLAHE-enhanced image, useful
    for showing the health worker what the model actually "sees"."""
    pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    image_rgb = np.array(pil_image)
    image_rgb = _center_crop_square(image_rgb)
    image_rgb = cv2.resize(image_rgb, (img_size, img_size), interpolation=cv2.INTER_AREA)
    image_rgb = _apply_clahe(image_rgb)

    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("Failed to encode preview image")
    return buf.tobytes()
