"""
Fine-tune EfficientNet-B4 on the APTOS 2019 Blindness Detection dataset.

This is the script version of notebooks/train_efficientnet_aptos.ipynb --
use whichever you prefer. Designed to run on Google Colab's free GPU tier,
but works on any CUDA or CPU machine.

--------------------------------------------------------------------------
1. Get the data (requires a free Kaggle account + API token):

    pip install kaggle
    export KAGGLE_USERNAME=your_username
    export KAGGLE_KEY=your_key
    kaggle competitions download -c aptos2019-blindness-detection -p data/
    unzip -q data/aptos2019-blindness-detection.zip -d data/aptos2019

   Expected resulting layout:
     data/aptos2019/train_images/*.png
     data/aptos2019/train.csv   (columns: id_code, diagnosis)

2. Install training dependencies:

    pip install -r requirements-training.txt

3. Run:

    python train_efficientnet_aptos.py --data-dir data/aptos2019 --epochs 20

4. Copy the resulting checkpoint into the backend and flip the mode:

    cp checkpoints/best_model.pth \
       ../backend/app/ml/weights/best_model.pth
    # then set MODEL_MODE=production in backend/.env
--------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import copy
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import cohen_kappa_score
from sklearn.model_selection import train_test_split
from torch import nn, optim
from torch.utils.data import DataLoader, Dataset
import timm
from torchvision import transforms

NUM_CLASSES = 5
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def apply_clahe(image_rgb: np.ndarray) -> np.ndarray:
    """Same CLAHE preprocessing used by the inference API, so the model
    trains on exactly the distribution it will see in production."""
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


class APTOSDataset(Dataset):
    def __init__(self, df: pd.DataFrame, images_dir: Path, img_size: int, train: bool):
        self.df = df.reset_index(drop=True)
        self.images_dir = images_dir
        self.img_size = img_size
        self.train = train

        aug = [
            transforms.ToPILImage(),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(20),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        plain = [
            transforms.ToPILImage(),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        self.transform = transforms.Compose(aug if train else plain)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int):
        row = self.df.iloc[idx]
        img_path = self.images_dir / f"{row['id_code']}.png"
        image_bgr = cv2.imread(str(img_path))
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        h, w = image_rgb.shape[:2]
        side = min(h, w)
        top, left = (h - side) // 2, (w - side) // 2
        image_rgb = image_rgb[top : top + side, left : left + side]
        image_rgb = cv2.resize(image_rgb, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA)
        image_rgb = apply_clahe(image_rgb)

        tensor = self.transform(image_rgb)
        label = int(row["diagnosis"])
        return tensor, label


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
def build_model() -> nn.Module:
    # NOTE: uses timm's EfficientNet-B4, not torchvision's -- the two have
    # different internal layer names, so checkpoints from one won't load
    # into the other. The VisionGuard AI backend expects timm checkpoints.
    return timm.create_model("efficientnet_b4", pretrained=True, num_classes=NUM_CLASSES)


# ---------------------------------------------------------------------------
# Train / eval loops
# ---------------------------------------------------------------------------
def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    model.train() if train else model.eval()
    total_loss, all_preds, all_labels = 0.0, [], []

    with torch.set_grad_enabled(train):
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            if train:
                optimizer.zero_grad()

            outputs = model(images)
            loss = criterion(outputs, labels)

            if train:
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * images.size(0)
            all_preds.extend(outputs.argmax(dim=1).cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    avg_loss = total_loss / len(loader.dataset)
    # Quadratic Weighted Kappa is the standard APTOS competition metric --
    # it penalizes predictions further from the true grade more heavily,
    # which matters clinically (mistaking Grade 0 for Grade 4 is worse
    # than mistaking Grade 2 for Grade 3).
    qwk = cohen_kappa_score(all_labels, all_preds, weights="quadratic")
    accuracy = float(np.mean(np.array(all_preds) == np.array(all_labels)))
    return avg_loss, accuracy, qwk


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, required=True, help="Path to unzipped APTOS 2019 data")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--img-size", type=int, default=380)
    parser.add_argument("--val-split", type=float, default=0.15)
    parser.add_argument("--output-dir", type=Path, default=Path("checkpoints"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    df = pd.read_csv(args.data_dir / "train.csv")
    train_df, val_df = train_test_split(
        df, test_size=args.val_split, stratify=df["diagnosis"], random_state=args.seed
    )
    print(f"Train: {len(train_df)}  Val: {len(val_df)}")

    images_dir = args.data_dir / "train_images"
    train_ds = APTOSDataset(train_df, images_dir, args.img_size, train=True)
    val_ds = APTOSDataset(val_df, images_dir, args.img_size, train=False)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)

    model = build_model().to(device)

    # Class weights to counter APTOS's heavy "No DR" imbalance.
    class_counts = train_df["diagnosis"].value_counts().sort_index()
    weights = torch.tensor((1.0 / class_counts.values), dtype=torch.float32)
    weights = (weights / weights.sum() * NUM_CLASSES).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)

    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", patience=2, factor=0.5)

    best_qwk = -1.0
    best_state = None

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss, train_acc, train_qwk = run_epoch(model, train_loader, criterion, optimizer, device, train=True)
        val_loss, val_acc, val_qwk = run_epoch(model, val_loader, criterion, optimizer, device, train=False)
        scheduler.step(val_qwk)

        print(
            f"Epoch {epoch:02d}/{args.epochs} ({time.time() - t0:.0f}s) | "
            f"train loss {train_loss:.4f} acc {train_acc:.3f} qwk {train_qwk:.3f} | "
            f"val loss {val_loss:.4f} acc {val_acc:.3f} qwk {val_qwk:.3f}"
        )

        if val_qwk > best_qwk:
            best_qwk = val_qwk
            best_state = copy.deepcopy(model.state_dict())
            torch.save({"model_state_dict": best_state, "val_qwk": best_qwk, "epoch": epoch}, args.output_dir / "best_model.pth")
            print(f"  ↳ New best QWK {best_qwk:.4f} — checkpoint saved")

    print(f"\nTraining complete. Best validation QWK: {best_qwk:.4f}")
    print(f"Best checkpoint: {args.output_dir / 'best_model.pth'}")
    print(
        "\nTo use this model in the app: copy the checkpoint to "
        "backend/app/ml/weights/best_model.pth and set MODEL_MODE=production "
        "in backend/.env"
    )


if __name__ == "__main__":
    main()
