#!/usr/bin/env python3
"""Export a trained checkpoint to an edge-friendly inference format."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--format", choices=["onnx", "openvino", "engine"], default="onnx")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--half", action="store_true")
    args = parser.parse_args()

    from ultralytics import YOLO

    exported = YOLO(str(args.model)).export(
        format=args.format,
        imgsz=args.image_size,
        half=args.half,
        dynamic=args.format == "onnx",
        simplify=args.format == "onnx",
    )
    print(exported)


if __name__ == "__main__":
    main()
