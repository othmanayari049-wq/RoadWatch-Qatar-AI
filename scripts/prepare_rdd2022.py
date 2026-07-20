#!/usr/bin/env python3
"""Convert extracted RDD2022 Pascal VOC annotations to Ultralytics YOLO format."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from roadwatch.training.rdd2022 import prepare_dataset


def normalized_countries(values: list[str]) -> frozenset[str]:
    return frozenset(value.strip().lower().replace("-", "_") for value in values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/processed/rdd2022"))
    parser.add_argument("--validation-country", action="append", default=[])
    parser.add_argument("--test-country", action="append", default=[])
    args = parser.parse_args()
    summary = prepare_dataset(
        raw_root=args.raw_root,
        output_root=args.output,
        validation_countries=normalized_countries(args.validation_country),
        test_countries=normalized_countries(args.test_country),
    )
    print(json.dumps(asdict(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
