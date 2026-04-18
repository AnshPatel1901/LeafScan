"""Train a plant disease classifier on PlantVillage-style datasets.

Expected dataset layout:
    dataset_root/
      ClassA/
      ClassB/
      ...

Class names should follow PlantVillage naming like:
    Tomato___Early_blight
    Tomato___healthy

Training is two-phase:
    Phase 1 — frozen base (MobileNetV2) + custom head, Adam 1e-3
    Phase 2 — fine-tune top 30 layers of MobileNetV2, Adam 1e-5
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

# Disable oneDNN/MKL optimizations — prevents "could not create a memory object"
# crash on large datasets with Intel MKL convolutions.
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
# Suppress verbose TF startup logs (keep warnings + errors only).
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

tf = None
AUTOTUNE = None


def get_tf():
    global tf, AUTOTUNE
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
    AUTOTUNE = tf.data.AUTOTUNE
    return tf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train disease classification model")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("../plantvillage dataset/color"),
        help="Path to dataset directory with class subfolders",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models"),
        help="Where model artifacts will be written",
    )
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=12,
                        help="Phase 1 (frozen base) epochs")
    parser.add_argument("--fine-tune-epochs", type=int, default=6,
                        help="Phase 2 (fine-tune) epochs")
    parser.add_argument("--fine-tune-layers", type=int, default=30,
                        help="Number of top MobileNetV2 layers to unfreeze for fine-tuning")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-split", type=float, default=0.2)
    parser.add_argument("--skip-fine-tune", action="store_true",
                        help="Skip phase 2 fine-tuning (faster, lower accuracy)")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick training preset: fewer epochs and no fine-tuning",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume interrupted training from backup state when available (default: on)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Disable automatic resume from backup state",
    )
    return parser.parse_args()


def split_label(class_name: str) -> tuple[str, str]:
    if "___" in class_name:
        plant, disease = class_name.split("___", 1)
    else:
        plant, disease = class_name, "unknown"

    plant = plant.replace("_", " ").replace(",", " ").strip()
    disease = disease.replace("_", " ").strip()
    return plant, disease


def make_datasets(args: argparse.Namespace) -> tuple[Any, Any, list[str]]:
    tf_local = get_tf()
    train_ds = tf.keras.utils.image_dataset_from_directory(
        args.dataset_dir,
        labels="inferred",
        label_mode="int",
        validation_split=args.validation_split,
        subset="training",
        seed=args.seed,
        image_size=(args.img_size, args.img_size),
        batch_size=args.batch_size,
    )

    val_ds = tf_local.keras.utils.image_dataset_from_directory(
        args.dataset_dir,
        labels="inferred",
        label_mode="int",
        validation_split=args.validation_split,
        subset="validation",
        seed=args.seed,
        image_size=(args.img_size, args.img_size),
        batch_size=args.batch_size,
    )

    class_names = train_ds.class_names

    # Do NOT cache train_ds — 43k images at 224×224 would exhaust RAM (~26 GB).
    # Shuffle + prefetch is sufficient; caching is only safe for val_ds (10k images).
    train_ds = train_ds.shuffle(500).prefetch(AUTOTUNE)
    val_ds = val_ds.cache().prefetch(AUTOTUNE)
    return train_ds, val_ds, class_names


def build_model(num_classes: int, img_size: int) -> Any:
    tf_local = get_tf()
    data_augmentation = tf_local.keras.Sequential(
        [
            tf_local.keras.layers.RandomFlip("horizontal"),
            tf_local.keras.layers.RandomRotation(0.08),
            tf_local.keras.layers.RandomZoom(0.12),
            tf_local.keras.layers.RandomBrightness(0.1),
            tf_local.keras.layers.RandomContrast(0.1),
        ],
        name="augmentation",
    )

    inputs = tf_local.keras.Input(shape=(img_size, img_size, 3))
    x = data_augmentation(inputs)
    x = tf_local.keras.applications.mobilenet_v2.preprocess_input(x)

    base_model = tf_local.keras.applications.MobileNetV2(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False  # Phase 1: freeze entire base

    x = base_model(x, training=False)
    x = tf_local.keras.layers.GlobalAveragePooling2D()(x)
    x = tf_local.keras.layers.Dropout(0.2)(x)
    outputs = tf_local.keras.layers.Dense(num_classes, activation="softmax")(x)

    model = tf_local.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf_local.keras.optimizers.Adam(learning_rate=1e-3),
        loss=tf_local.keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )
    return model


def fine_tune_model(model: Any, num_fine_tune_layers: int) -> Any:
    """
    Unfreeze the top *num_fine_tune_layers* of the MobileNetV2 base and
    recompile with a low learning rate for phase-2 training.
    """
    tf_local = get_tf()

    # Locate the MobileNetV2 backbone inside the composite model.
    base_model = None
    for layer in model.layers:
        if isinstance(layer, tf_local.keras.Model) and "mobilenetv2" in layer.name.lower():
            base_model = layer
            break
    # Fallback: find by broader name pattern.
    if base_model is None:
        for layer in model.layers:
            if isinstance(layer, tf_local.keras.Model) and "mobilenet" in layer.name.lower():
                base_model = layer
                break

    if base_model is None:
        print("WARNING: Could not locate MobileNetV2 base — skipping fine-tune")
        return model

    base_model.trainable = True
    # Freeze all but the last num_fine_tune_layers
    for layer in base_model.layers[:-num_fine_tune_layers]:
        layer.trainable = False

    trainable_count = sum(1 for l in base_model.layers if l.trainable)
    print(f"Fine-tune: {trainable_count} / {len(base_model.layers)} base layers unfrozen")

    model.compile(
        optimizer=tf_local.keras.optimizers.Adam(learning_rate=1e-5),
        loss=tf_local.keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )
    return model


def write_label_map(class_names: list[str], output_path: Path) -> None:
    labels = []
    for idx, cls in enumerate(class_names):
        plant_name, disease_name = split_label(cls)
        labels.append(
            {
                "index": idx,
                "class_name": cls,
                "plant_name": plant_name,
                "disease_name": disease_name,
            }
        )

    output_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")


def main() -> None:
    tf_local = get_tf()

    # Use all CPU cores for both inter-op (parallel ops) and intra-op (within op)
    # 0 = let TF pick the optimal thread count automatically
    tf_local.config.threading.set_inter_op_parallelism_threads(0)
    tf_local.config.threading.set_intra_op_parallelism_threads(0)

    args = parse_args()

    if args.quick:
        # Quick mode prioritizes speed over best final accuracy.
        args.epochs = min(args.epochs, 6)
        args.fine_tune_epochs = 0
        args.skip_fine_tune = True
        if args.img_size > 192:
            args.img_size = 192

    # Enable mixed precision automatically when GPU is available.
    gpus = tf_local.config.list_physical_devices("GPU")
    if gpus:
        tf_local.keras.mixed_precision.set_global_policy("mixed_float16")
        print(f"Detected {len(gpus)} GPU(s): mixed_float16 enabled")
    else:
        print("No GPU detected: running with float32 on CPU")

    dataset_dir = args.dataset_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    train_ds, val_ds, class_names = make_datasets(args)
    model = build_model(num_classes=len(class_names), img_size=args.img_size)

    # ── Phase 1: frozen base ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Phase 1: Training head with frozen MobileNetV2 base")
    print(f"Classes: {len(class_names)}  |  Epochs: {args.epochs}")
    print(f"{'='*60}\n")

    checkpoint_path = output_dir / "disease_model_best.keras"
    phase1_callbacks = [
        tf_local.keras.callbacks.ModelCheckpoint(
            filepath=str(checkpoint_path),
            monitor="val_accuracy",
            save_best_only=True,
            mode="max",
            verbose=1,
        ),
        tf_local.keras.callbacks.BackupAndRestore(
            backup_dir=str(output_dir / "backup_phase1"),
            delete_checkpoint=False,
            save_freq="epoch",
        ) if args.resume else None,
        tf_local.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=3,
            mode="max",
            restore_best_weights=True,
        ),
        tf_local.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.3,
            patience=2,
            min_lr=1e-6,
            verbose=1,
        ),
    ]
    phase1_callbacks = [cb for cb in phase1_callbacks if cb is not None]

    history1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=phase1_callbacks,
    )

    loss1, acc1 = model.evaluate(val_ds, verbose=0)
    print(f"\nPhase 1 complete — val_accuracy={acc1:.4f}  val_loss={loss1:.4f}")

    # ── Phase 2: fine-tune top layers ─────────────────────────────────────────
    if not args.skip_fine_tune and args.fine_tune_epochs > 0:
        print(f"\n{'='*60}")
        print(f"Phase 2: Fine-tuning top {args.fine_tune_layers} MobileNetV2 layers")
        print(f"Epochs: {args.fine_tune_epochs}  |  LR: 1e-5")
        print(f"{'='*60}\n")

        model = fine_tune_model(model, num_fine_tune_layers=args.fine_tune_layers)

        fine_tune_checkpoint = output_dir / "disease_model_best_finetuned.keras"
        phase2_callbacks = [
            tf_local.keras.callbacks.ModelCheckpoint(
                filepath=str(fine_tune_checkpoint),
                monitor="val_accuracy",
                save_best_only=True,
                mode="max",
                verbose=1,
            ),
            tf_local.keras.callbacks.BackupAndRestore(
                backup_dir=str(output_dir / "backup_phase2"),
                delete_checkpoint=False,
                save_freq="epoch",
            ) if args.resume else None,
            tf_local.keras.callbacks.EarlyStopping(
                monitor="val_accuracy",
                patience=3,
                mode="max",
                restore_best_weights=True,
            ),
            tf_local.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.3,
                patience=2,
                min_lr=1e-7,
                verbose=1,
            ),
        ]
        phase2_callbacks = [cb for cb in phase2_callbacks if cb is not None]

        history2 = model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=args.fine_tune_epochs,
            callbacks=phase2_callbacks,
        )

        loss2, acc2 = model.evaluate(val_ds, verbose=0)
        print(f"\nPhase 2 complete — val_accuracy={acc2:.4f}  val_loss={loss2:.4f}")

        # Use fine-tuned accuracy for final metrics
        loss, acc = loss2, acc2
        total_epochs = (
            len(history1.history.get("loss", []))
            + len(history2.history.get("loss", []))
        )
        fine_tuned = True
    else:
        loss, acc = loss1, acc1
        total_epochs = len(history1.history.get("loss", []))
        fine_tuned = False

    # ── Save final model ──────────────────────────────────────────────────────
    final_model_path = output_dir / "disease_model.keras"
    model.save(final_model_path)

    write_label_map(class_names, output_dir / "label_map.json")

    metrics = {
        "val_loss": float(loss),
        "val_accuracy": float(acc),
        "num_classes": len(class_names),
        "epochs_trained": total_epochs,
        "img_size": args.img_size,
        "batch_size": args.batch_size,
        "fine_tuned": fine_tuned,
        "fine_tune_layers": args.fine_tune_layers if fine_tuned else 0,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\nTraining complete")
    print(f"  Model saved       : {final_model_path}")
    print(f"  Best checkpoint   : {checkpoint_path}")
    if fine_tuned:
        print(f"  Fine-tuned ckpt   : {fine_tune_checkpoint}")
    print(f"  Label map saved   : {output_dir / 'label_map.json'}")
    print(f"  Validation accuracy: {acc:.4f}")


if __name__ == "__main__":
    main()
