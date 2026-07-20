# RoadWatch detector model card

## Model status

**No trained checkpoint or benchmark result is shipped in this repository.** The codebase
contains a reproducible training and evaluation recipe. This distinction prevents a generic
pretrained object detector, unverified third-party weights, or invented metrics from being
presented as a validated road-damage model.

Update this card with artifact-specific provenance and measured results whenever a checkpoint
is released.

## Reference model recipe

| Property | Reference configuration |
|---|---|
| Task | Object detection |
| Base architecture | Ultralytics YOLO26n pretrained checkpoint |
| Target labels | D00, D10, D20, D40 |
| Input size | 640 × 640 |
| Optimizer | AdamW |
| Maximum epochs | 100 |
| Early-stopping patience | 20 epochs |
| Seed | 42 |
| Deterministic mode | Enabled |
| Primary evaluation | mAP50-95 and per-class AP |
| Deployment checkpoint | `models/best.pt` |

Ultralytics documents the current training, validation, prediction, and export APIs in its
[official documentation](https://docs.ultralytics.com/).

## Intended use

- Detect four visible road-damage categories in road-level imagery.
- Assist a human inspector in reviewing and prioritizing candidate defects.
- Support research and portfolio demonstrations of an end-to-end computer-vision system.
- Produce bounding boxes, confidence scores, and metadata for geospatial analysis.

## Out-of-scope use

- Autonomous road closure or maintenance authorization.
- Direct estimation of crack depth, physical dimensions, repair cost, or structural capacity.
- Pavement Condition Index certification.
- Enforcement, surveillance, identity recognition, or vehicle tracking.
- Safety-critical deployment without local validation and qualified human review.
- Claiming that absence of a detection proves a road is undamaged.

## Inspection-priority heuristic

The API adds a transparent score after detection:

\[
S = 100\left(0.45c + 0.35\min\left(\frac{a}{0.10},1\right) + 0.20p_k\right)
\]

where:

- \(c\) is model confidence from 0 to 1;
- \(a\) is the bounding-box area divided by image area;
- \(p_k\) is a documented class prior: 0.35 (D00), 0.45 (D10), 0.75 (D20), or 1.00
  (D40).

Scores below 40 are labeled low, scores from 40 to below 70 are medium, and scores of 70 or
more are high. The area contribution saturates at 10% of the image because perspective makes
pixel area unsuitable as a physical measurement.

This score is an explainable triage heuristic. It is not learned from maintenance outcomes,
calibrated to failure risk, or equivalent to engineering severity.

## Required evaluation before release

Record all of the following for each checkpoint:

- immutable artifact digest and model version;
- code commit and complete training command;
- base checkpoint version and license;
- dataset release, countries, split method, and exact sample counts;
- per-class precision, recall, AP50, and AP50-95;
- confusion matrix and confidence calibration;
- latency distribution on named CPU, GPU, and edge hardware;
- error analysis for markings, patches, shadows, glare, night scenes, and blur;
- geographic holdout performance;
- independent Qatar acceptance-set results;
- reviewer identity, approval date, and deployment decision.

### Results template

| Split | D00 AP50-95 | D10 AP50-95 | D20 AP50-95 | D40 AP50-95 | Overall mAP50-95 |
|---|---:|---:|---:|---:|---:|
| Validation | Not measured | Not measured | Not measured | Not measured | Not measured |
| Geographic test | Not measured | Not measured | Not measured | Not measured | Not measured |
| Qatar acceptance | Not measured | Not measured | Not measured | Not measured | Not measured |

Do not replace “Not measured” with training-set performance or another repository's result.

## Limitations and risks

- The model can fail under domain shift and unfamiliar capture conditions.
- Confidence is not automatically a calibrated probability of physical damage.
- Bounding-box area changes with distance and perspective.
- Class-prior scoring can rank a confident pothole above a visually larger crack even when a
  field engineer would decide differently.
- Dataset annotation errors and class imbalance can propagate into predictions.
- A small model favors efficiency; larger models may improve detection at greater latency and
  resource cost.
- Model files can contain unsafe serialized objects. Accept weights only from the controlled
  training pipeline and scan artifacts before deployment.

## Human oversight

Every high-priority detection and sampled lower-priority/negative image should be reviewable
by a qualified operator. Operational processes need escalation, correction, audit, and model
rollback paths. Maintenance decisions must use field measurements and applicable engineering
standards in addition to image-based evidence.

