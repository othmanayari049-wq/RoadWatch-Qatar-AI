# Qatar pilot acceptance protocol

## Status and purpose

This is a planning protocol for a future road-inspection pilot. It does not grant operational
approval and does not establish RoadWatch performance in Qatar. Its purpose is to make local
evaluation reproducible before any field trial or maintenance workflow is considered.

## Evaluation question

For which Qatar road conditions, capture devices, damage classes, and operating constraints can
the candidate checkpoint assist a qualified inspector in finding visible defects that need
field verification?

The pilot must evaluate the full workflow: image capture, upload checks, detector output,
inspection-priority heuristic, reviewer interpretation, and reporting. A bounding box,
confidence score, or priority label is not a maintenance decision.

## Data governance and collection record

Before collection, document the approved purpose, access roles, retention period, redaction
process, and required legal or institutional approvals. Do not publish raw imagery, faces,
license plates, private property, precise locations, or identifiers without permission.

For every capture session, record:

- device and camera configuration;
- capture date and time of day;
- municipality, road category, and protected road-segment identifier;
- weather, glare, shadows, dust, wet surface, and lighting condition;
- camera height, direction, approximate speed, and image-quality outcome;
- model version, artifact digest, software commit, and inference configuration.

## Reference labels

Use trained independent reviewers to label the four supported visible RDD2022 categories:
`D00`, `D10`, `D20`, and `D40`. Preserve disagreement records and document adjudication.
Include negative and difficult non-damage examples such as road markings, patches, utility
covers, shadows, glare, repaired surfaces, and construction areas.

These labels describe visible imagery only. They must not be used as proxies for crack depth,
structural capacity, Pavement Condition Index, repair cost, or urgency.

## Split design

The unit of separation is a road segment or capture session, not an individual frame. Nearby or
near-duplicate images must remain in the same split. Keep the local acceptance set isolated
from training, tuning, threshold selection, and post-hoc model choices.

Report the number of images, road segments, sessions, annotators, and detections in every
split. Document exclusions before examining final results.

## Required analysis

Report overall and per-class precision, recall, AP50, AP50-95, confusion matrix,
false-negative review, inference latency, and confidence calibration. Break down results by
road category, municipality, lighting and surface condition, device, and camera setup where
sample size permits.

Record uncertain cases and failure modes. A strong overall metric cannot replace a material
failure in an important condition or road type.

## Human-review trial

Test whether the dashboard, map, filters, report, and priority labels help reviewers find and
verify candidate defects without hiding the original image. Include clear escalation steps and
a way to correct model output.

## Acceptance decision

The final report must identify the exact model artifact, dataset version, code commit,
configuration, results, known failures, reviewer approvals, and decision. Valid outcomes
include restricted use, further data collection, model revision, or no deployment.

RoadWatch remains decision support: field verification and applicable engineering standards
are required before maintenance action.
