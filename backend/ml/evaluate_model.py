"""Evaluate a trained Keras disease model on a dataset directory.

Outputs:
  - Overall accuracy / loss (stdout + JSON)
  - Per-class precision, recall, F1 (classification report)
  - Confusion matrix saved as confusion_matrix.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

tf = None


def get_tf():
    global tf
    if tf is not None:
        return tf

    try:
        import tensorflow as tensorflow_module  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "TensorFlow is not installed in this environment. "
            "Activate your Python 3.11 ML env and run: pip install -r requirements-ml.txt"
        ) from exc

    tf = tensorflow_module
    return tf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate trained disease model")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("../plantvillage dataset/color"),
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("models/disease_model.keras"),
    )
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save evaluation artifacts (default: same as model-path parent)",
    )
    return parser.parse_args()


def main() -> None:
    tf_local = get_tf()
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    model_path = args.model_path.resolve()
    output_dir = (args.output_dir or model_path.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # ── Load dataset ──────────────────────────────────────────────────────────
    ds = tf_local.keras.utils.image_dataset_from_directory(
        dataset_dir,
        labels="inferred",
        label_mode="int",
        image_size=(args.img_size, args.img_size),
        batch_size=args.batch_size,
        shuffle=False,
    )
    class_names: list[str] = ds.class_names

    # ── Load model ────────────────────────────────────────────────────────────
    model: Any = tf_local.keras.models.load_model(model_path)
    loss, acc = model.evaluate(ds, verbose=1)

    # ── Build predictions for detailed metrics ────────────────────────────────
    try:
        import numpy as np
        from sklearn.metrics import classification_report, confusion_matrix  # type: ignore[import-untyped]

        y_true, y_pred = [], []
        for images, labels in ds:
            preds = model.predict(images, verbose=0)
            y_true.extend(labels.numpy().tolist())
            y_pred.extend(np.argmax(preds, axis=1).tolist())

        # Classification report
        report_str = classification_report(
            y_true, y_pred, target_names=class_names, digits=4, zero_division=0
        )
        print("\n" + "=" * 60)
        print("Per-class metrics")
        print("=" * 60)
        print(report_str)

        report_dict = classification_report(
            y_true, y_pred, target_names=class_names, digits=4,
            zero_division=0, output_dict=True
        )

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        cm_path = output_dir / "confusion_matrix.json"
        cm_path.write_text(
            json.dumps(
                {
                    "class_names": class_names,
                    "matrix": cm.tolist(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Confusion matrix saved: {cm_path}")

        per_class = {
            cls: {
                "precision": float(report_dict[cls]["precision"]),
                "recall":    float(report_dict[cls]["recall"]),
                "f1":        float(report_dict[cls]["f1-score"]),
                "support":   int(report_dict[cls]["support"]),
            }
            for cls in class_names
            if cls in report_dict
        }

    except ImportError:
        print(
            "\nWARNING: scikit-learn not installed — skipping per-class metrics. "
            "Run: pip install scikit-learn"
        )
        per_class = {}

    # ── Summary report ────────────────────────────────────────────────────────
    summary = {
        "dataset":     str(dataset_dir),
        "model":       str(model_path),
        "loss":        float(loss),
        "accuracy":    float(acc),
        "num_classes": len(class_names),
        "per_class":   per_class,
    }

    report_path = output_dir / "eval_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nEvaluation report saved: {report_path}")

    # Print overall summary
    print("\n" + "=" * 60)
    print(f"Overall  accuracy : {acc:.4f}  ({acc * 100:.2f}%)")
    print(f"Overall  loss     : {loss:.4f}")
    print(f"Classes            : {len(class_names)}")
    print("=" * 60)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
