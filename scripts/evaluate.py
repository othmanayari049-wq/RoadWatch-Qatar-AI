#!/usr/bin/env python3
"""Evaluate a trained checkpoint and write machine-readable detection metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--data", default="configs/rdd2022.yaml")
    parser.add_argument("--split", choices=["val", "test"], default="test")
    parser.add_argument("--device", default="0")
    parser.add_argument("--output", type=Path, default=Path("artifacts/metrics.json"))
    args = parser.parse_args()

    from ultralytics import YOLO

    metrics = YOLO(str(args.model)).val(
        data=args.data,
        split=args.split,
        device=args.device,
        plots=True,
        save_json=True,
    )
    payload = {
        "model": str(args.model),
        "split": args.split,
        "map50_95": float(metrics.box.map),
        "map50": float(metrics.box.map50),
        "map75": float(metrics.box.map75),
        "per_class_map50_95": [float(value) for value in metrics.box.maps],
        "class_names": metrics.names,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

