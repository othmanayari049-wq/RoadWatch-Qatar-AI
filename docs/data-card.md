# RDD2022 data card

## Dataset summary

RoadWatch's reference training pipeline uses the **Road Damage Dataset 2022 (RDD2022)**.
The official release contains 47,420 road images from Japan, India, the Czech Republic,
Norway, the United States, and China, with more than 55,000 annotated instances across four
damage categories.

| Code | Road damage category |
|---|---|
| D00 | Longitudinal crack |
| D10 | Transverse crack |
| D20 | Alligator crack |
| D40 | Pothole |

Primary sources:

- [Official RDD2022 release and files](https://doi.org/10.6084/m9.figshare.21431547)
- [RDD2022 data article](https://doi.org/10.1002/gdj3.260)
- [CRDDC 2022 challenge paper](https://doi.org/10.48550/arXiv.2211.11362)

The Figshare release is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Users must preserve attribution and independently confirm that their planned use complies
with the dataset and software licenses.

## Intended use

- Benchmark image-based road-damage detection.
- Train models that help prioritize images for human inspection.
- Study cross-country generalization and domain shift.
- Support research prototypes for low-cost road monitoring.

The dataset does not by itself validate a model for maintenance decisions, Qatar roads, or
physical severity measurement.

## Preparation in this repository

`scripts/download_rdd2022.py` reads official Figshare metadata, restricts downloads to
allowlisted HTTPS hosts, and verifies every archive against the published MD5 checksum.

`scripts/prepare_rdd2022.py`:

- safely parses Pascal VOC XML with `defusedxml`;
- retains the four documented RDD2022 classes;
- clips boxes to image boundaries and rejects invalid boxes;
- converts annotations to normalized YOLO format;
- detects duplicate output filenames;
- produces train, validation, and test directories;
- reports image, object, skipped-label, class, and split counts.

Example with geographic holdouts:

```bash
python scripts/prepare_rdd2022.py data/raw/rdd2022-extracted \
  --validation-country norway \
  --test-country united_states
```

Holding out complete countries is preferable when the research question is geographic
generalization. If no country holdouts are supplied, a stable SHA-256-based 80/10/10 image
split is used. The random-like split is convenient, but nearby video frames could appear in
different splits; it should not be used to make strong claims about unseen-road performance.

## Known representation gaps

- Qatar is not one of the six collection countries.
- Road materials, repair practices, camera mounting, lane markings, climate, lighting,
  traffic, dust, and shadows may differ from a Qatar deployment.
- Image-space bounding boxes do not provide crack depth, physical width, defect volume, or
  Pavement Condition Index.
- Class frequencies and image capture conditions may be imbalanced.
- Visually similar road markings, patches, shadows, and utility covers can create false
  positives.
- Fine damage, occluded damage, glare, motion blur, and night images can create false
  negatives.

## Qatar acceptance dataset requirement

Before an operational pilot, collect a separate local evaluation set with appropriate
permissions and governance. It should cover:

- multiple municipalities and road categories;
- daytime, night, glare, dust, shadows, and wet-road conditions;
- multiple devices, focal lengths, camera heights, and vehicle speeds;
- repaired surfaces, road markings, utility covers, and construction zones;
- independent annotation by trained reviewers with adjudication;
- location-level grouping so near-duplicate road segments cannot cross splits.

Keep the local acceptance set isolated from model development. Report results by class,
lighting condition, device, location, and relevant road type—not only one overall score.

## Privacy and safety

Street imagery may unintentionally include faces, license plates, homes, or location
metadata. Collection programs should apply local legal review, notice and permission where
required, data minimization, access control, retention limits, and redaction before sharing.
The reference API does not persist uploaded image bytes, but operators remain responsible
for the upstream collection and downstream copies.

