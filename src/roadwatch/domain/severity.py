"""Explainable inspection-priority scoring.

The score is a triage heuristic, not a civil-engineering condition assessment.
It combines model confidence, visible area, and a configurable class prior.
"""

from dataclasses import dataclass

from roadwatch.domain.models import DamageClass, Severity


@dataclass(frozen=True, slots=True)
class SeverityAssessment:
    score: float
    level: Severity


CLASS_PRIOR: dict[DamageClass, float] = {
    DamageClass.LONGITUDINAL_CRACK: 0.35,
    DamageClass.TRANSVERSE_CRACK: 0.45,
    DamageClass.ALLIGATOR_CRACK: 0.75,
    DamageClass.POTHOLE: 1.00,
}


def assess_severity(
    damage_class: DamageClass,
    confidence: float,
    area_ratio: float,
) -> SeverityAssessment:
    """Calculate a bounded and reproducible inspection-priority score.

    Visible damage covering 10% of the image saturates the area component because
    image perspective makes larger pixel ratios unreliable as physical measurements.
    """

    confidence = min(max(confidence, 0.0), 1.0)
    normalized_area = min(max(area_ratio, 0.0) / 0.10, 1.0)
    raw = 100 * (0.45 * confidence + 0.35 * normalized_area + 0.20 * CLASS_PRIOR[damage_class])
    score = round(min(max(raw, 0.0), 100.0), 1)

    if score < 40:
        level = Severity.LOW
    elif score < 70:
        level = Severity.MEDIUM
    else:
        level = Severity.HIGH
    return SeverityAssessment(score=score, level=level)
