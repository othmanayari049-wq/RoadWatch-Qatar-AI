from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from roadwatch.training.rdd2022 import (
    deterministic_split,
    infer_country,
    parse_voc_annotation,
    prepare_dataset,
    to_yolo_lines,
)

VOC_XML = """\
<annotation>
  <filename>road_001.jpg</filename>
  <size><width>1000</width><height>500</height><depth>3</depth></size>
  <object>
    <name>D40</name>
    <bndbox><xmin>100</xmin><ymin>50</ymin><xmax>300</xmax><ymax>150</ymax></bndbox>
  </object>
  <object>
    <name>D99</name>
    <bndbox><xmin>1</xmin><ymin>1</ymin><xmax>2</xmax><ymax>2</ymax></bndbox>
  </object>
</annotation>
"""


def create_fixture_dataset(root: Path) -> Path:
    country = root / "RDD2022_Japan" / "train"
    annotations = country / "annotations" / "xmls"
    images = country / "images"
    annotations.mkdir(parents=True)
    images.mkdir(parents=True)
    xml_path = annotations / "road_001.xml"
    xml_path.write_text(VOC_XML, encoding="utf-8")
    Image.new("RGB", (1000, 500), color="gray").save(images / "road_001.jpg")
    return xml_path


def test_parse_and_convert_voc(tmp_path: Path) -> None:
    annotation, skipped = parse_voc_annotation(create_fixture_dataset(tmp_path))
    lines = to_yolo_lines(annotation)
    assert skipped == 1
    assert lines == ["3 0.200000 0.200000 0.200000 0.200000"]


def test_country_inference() -> None:
    assert infer_country(Path("RDD2022_United_States/train/a.xml")) == "united_states"
    assert infer_country(Path("RDD2022_Japan/train/a.xml")) == "japan"
    assert infer_country(Path("unrecognized/a.xml")) == "unknown"


def test_deterministic_split_is_stable() -> None:
    path = Path("country/annotations/image_001.xml")
    assert deterministic_split(path) == deterministic_split(path)
    assert deterministic_split(path) in {"train", "val", "test"}


def test_prepare_dataset_with_country_holdout(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    create_fixture_dataset(raw)
    output = tmp_path / "processed"
    summary = prepare_dataset(
        raw,
        output,
        validation_countries=frozenset({"japan"}),
    )
    assert summary.images == 1
    assert summary.objects == 1
    assert summary.skipped_objects == 1
    assert summary.split_counts == {"val": 1}
    assert (output / "images/val/road_001.jpg").is_file()
    assert (output / "labels/val/road_001.txt").read_text() == (
        "3 0.200000 0.200000 0.200000 0.200000"
    )


def test_prepare_rejects_overlapping_holdouts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot overlap"):
        prepare_dataset(
            tmp_path,
            tmp_path / "output",
            validation_countries=frozenset({"japan"}),
            test_countries=frozenset({"japan"}),
        )
