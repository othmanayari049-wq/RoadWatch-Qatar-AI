"""RDD2022 Pascal VOC parsing and deterministic YOLO dataset preparation."""

from __future__ import annotations

import hashlib
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as ET

from roadwatch.domain.models import DamageClass

CLASS_INDEX = {item.value: index for index, item in enumerate(DamageClass)}
SUPPORTED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")


@dataclass(frozen=True, slots=True)
class VocObject:
    label: DamageClass
    xmin: float
    ymin: float
    xmax: float
    ymax: float


@dataclass(frozen=True, slots=True)
class VocAnnotation:
    filename: str
    width: int
    height: int
    objects: tuple[VocObject, ...]


@dataclass(frozen=True, slots=True)
class PreparationSummary:
    images: int
    objects: int
    skipped_objects: int
    split_counts: dict[str, int]
    class_counts: dict[str, int]


def parse_voc_annotation(path: Path) -> tuple[VocAnnotation, int]:
    """Parse supported RDD2022 objects, returning the number of skipped labels."""

    root = ET.parse(path).getroot()
    if root is None:
        raise ValueError(f"Empty XML annotation: {path}")
    filename = required_text(root, "filename")
    size = root.find("size")
    if size is None:
        raise ValueError(f"Missing image size in {path}")
    width = int(required_text(size, "width"))
    height = int(required_text(size, "height"))
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image dimensions in {path}")

    objects: list[VocObject] = []
    skipped = 0
    for element in root.findall("object"):
        raw_label = required_text(element, "name").strip().upper()
        try:
            label = DamageClass(raw_label)
        except ValueError:
            skipped += 1
            continue
        box = element.find("bndbox")
        if box is None:
            skipped += 1
            continue
        xmin = max(0.0, float(required_text(box, "xmin")))
        ymin = max(0.0, float(required_text(box, "ymin")))
        xmax = min(float(width), float(required_text(box, "xmax")))
        ymax = min(float(height), float(required_text(box, "ymax")))
        if xmax <= xmin or ymax <= ymin:
            skipped += 1
            continue
        objects.append(VocObject(label, xmin, ymin, xmax, ymax))

    return VocAnnotation(filename, width, height, tuple(objects)), skipped


def required_text(parent: Element[str], name: str) -> str:
    element = parent.find(name)
    if element is None or element.text is None or not element.text.strip():
        raise ValueError(f"Missing required XML value: {name}")
    return element.text.strip()


def to_yolo_lines(annotation: VocAnnotation) -> list[str]:
    """Convert pixel-space VOC boxes to normalized YOLO ``xywh`` rows."""

    lines: list[str] = []
    for item in annotation.objects:
        x_center = ((item.xmin + item.xmax) / 2) / annotation.width
        y_center = ((item.ymin + item.ymax) / 2) / annotation.height
        width = (item.xmax - item.xmin) / annotation.width
        height = (item.ymax - item.ymin) / annotation.height
        lines.append(
            f"{CLASS_INDEX[item.label.value]} {x_center:.6f} {y_center:.6f} "
            f"{width:.6f} {height:.6f}"
        )
    return lines


def deterministic_split(relative_path: Path) -> str:
    """Stable 80/10/10 split used when no geographic holdout is requested."""

    digest = hashlib.sha256(relative_path.as_posix().encode()).digest()
    bucket = int.from_bytes(digest[:4], "big") % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "val"
    return "test"


def infer_country(path: Path) -> str:
    """Infer a country key from common RDD2022 directory/archive names."""

    candidates = {
        "czech": "czech",
        "india": "india",
        "japan": "japan",
        "norway": "norway",
        "united_states": "united_states",
        "unitedstates": "united_states",
        "usa": "united_states",
        "china": "china",
    }
    normalized_parts = [part.lower().replace("-", "_").replace(" ", "_") for part in path.parts]
    for part in normalized_parts:
        for needle, country in candidates.items():
            if needle in part:
                return country
    return "unknown"


def choose_split(
    relative_path: Path,
    validation_countries: frozenset[str],
    test_countries: frozenset[str],
) -> str:
    country = infer_country(relative_path)
    if country in test_countries:
        return "test"
    if country in validation_countries:
        return "val"
    if validation_countries or test_countries:
        return "train"
    return deterministic_split(relative_path)


def locate_image(xml_path: Path, filename: str, raw_root: Path) -> Path:
    """Find the annotation image without depending on one archive layout."""

    direct_candidates = [xml_path.with_name(filename), xml_path.parent / filename]
    for parent_name in ("images", "JPEGImages"):
        direct_candidates.append(xml_path.parent.parent / parent_name / filename)
    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate

    stem = Path(filename).stem
    matches: list[Path] = []
    for suffix in SUPPORTED_IMAGE_SUFFIXES:
        matches.extend(raw_root.rglob(f"{stem}{suffix}"))
        matches.extend(raw_root.rglob(f"{stem}{suffix.upper()}"))
    unique = sorted(set(matches))
    if len(unique) != 1:
        raise FileNotFoundError(
            f"Expected exactly one image for {xml_path}; found {len(unique)} matches"
        )
    return unique[0]


def prepare_dataset(
    raw_root: Path,
    output_root: Path,
    validation_countries: frozenset[str] = frozenset(),
    test_countries: frozenset[str] = frozenset(),
) -> PreparationSummary:
    """Convert all labeled XML files into a clean, reproducible YOLO dataset."""

    if validation_countries & test_countries:
        raise ValueError("Validation and test country holdouts cannot overlap")
    xml_paths = sorted(raw_root.rglob("*.xml"))
    if not xml_paths:
        raise FileNotFoundError(f"No Pascal VOC annotations found under {raw_root}")

    split_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    object_count = 0
    skipped_objects = 0

    for xml_path in xml_paths:
        relative = xml_path.relative_to(raw_root)
        annotation, skipped = parse_voc_annotation(xml_path)
        image_path = locate_image(xml_path, annotation.filename, raw_root)
        split = choose_split(relative, validation_countries, test_countries)
        image_destination = output_root / "images" / split / image_path.name
        label_destination = output_root / "labels" / split / f"{image_path.stem}.txt"
        image_destination.parent.mkdir(parents=True, exist_ok=True)
        label_destination.parent.mkdir(parents=True, exist_ok=True)

        if image_destination.exists() and image_destination.resolve() != image_path.resolve():
            raise FileExistsError(f"Duplicate output image name: {image_path.name}")
        shutil.copy2(image_path, image_destination)
        label_destination.write_text("\n".join(to_yolo_lines(annotation)), encoding="utf-8")

        split_counts[split] += 1
        object_count += len(annotation.objects)
        skipped_objects += skipped
        class_counts.update(item.label.value for item in annotation.objects)

    return PreparationSummary(
        images=len(xml_paths),
        objects=object_count,
        skipped_objects=skipped_objects,
        split_counts=dict(split_counts),
        class_counts=dict(class_counts),
    )
