"""Self-contained, printable HTML inspection reports."""

# ruff: noqa: E501 - keeping HTML template lines readable as complete elements

from __future__ import annotations

from html import escape

from roadwatch.domain.models import StoredInspection


def render_html_report(record: StoredInspection) -> str:
    """Render a portable report without embedding or persisting the road image."""

    prediction = record.prediction
    location = (
        f"{prediction.location.latitude:.6f}, {prediction.location.longitude:.6f}"
        if prediction.location
        else "Not provided"
    )
    maximum = prediction.maximum_severity
    rows = "".join(
        f"""
        <tr>
          <td>{escape(item.damage_class.value)}</td>
          <td>{escape(item.label)}</td>
          <td>{item.confidence:.1%}</td>
          <td>{item.area_ratio:.2%}</td>
          <td>{item.severity_score:.1f}</td>
          <td>{escape(item.severity.value.title())}</td>
          <td>{item.bbox.x1:.0f}, {item.bbox.y1:.0f}, {item.bbox.x2:.0f}, {item.bbox.y2:.0f}</td>
        </tr>
        """
        for item in prediction.detections
    )
    if not rows:
        rows = '<tr><td colspan="7">No supported damage detected above threshold.</td></tr>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RoadWatch inspection {prediction.id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #172033; margin: 2.5rem; line-height: 1.45; }}
    h1 {{ color: #0f766e; margin-bottom: .25rem; }}
    .subtitle {{ color: #64748b; margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .75rem; margin: 1.5rem 0; }}
    .card {{ border: 1px solid #dbe4ee; border-radius: .5rem; padding: .8rem; }}
    .label {{ color: #64748b; font-size: .78rem; text-transform: uppercase; }}
    .value {{ font-weight: 700; margin-top: .2rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; font-size: .9rem; }}
    th, td {{ border: 1px solid #dbe4ee; padding: .55rem; text-align: left; }}
    th {{ background: #f1f5f9; }}
    .notice {{ margin-top: 1.5rem; background: #fffbeb; border-left: 4px solid #f59e0b;
      padding: .8rem 1rem; }}
    footer {{ margin-top: 2rem; color: #64748b; font-size: .8rem; }}
    @media print {{ body {{ margin: 1cm; }} .grid {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <h1>RoadWatch Qatar AI</h1>
  <p class="subtitle">AI-assisted road inspection report</p>
  <div class="grid">
    <div class="card"><div class="label">Inspection ID</div><div class="value">{prediction.id}</div></div>
    <div class="card"><div class="label">Created</div><div class="value">{escape(prediction.created_at.isoformat())}</div></div>
    <div class="card"><div class="label">Source file</div><div class="value">{escape(record.source_filename)}</div></div>
    <div class="card"><div class="label">Location</div><div class="value">{escape(location)}</div></div>
    <div class="card"><div class="label">Model version</div><div class="value">{escape(prediction.model_version)}</div></div>
    <div class="card"><div class="label">Maximum priority</div><div class="value">{escape(maximum.value.title()) if maximum else "None"}</div></div>
    <div class="card"><div class="label">Detections</div><div class="value">{len(prediction.detections)}</div></div>
    <div class="card"><div class="label">Inference</div><div class="value">{prediction.inference_ms:.1f} ms</div></div>
    <div class="card"><div class="label">Image size</div><div class="value">{prediction.image_width} x {prediction.image_height}</div></div>
  </div>
  <h2>Detected damage</h2>
  <table>
    <thead><tr><th>Code</th><th>Class</th><th>Confidence</th><th>Visible area</th><th>Score</th><th>Priority</th><th>Bounding box (xyxy)</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="notice"><strong>Decision-support only.</strong> Priority is an image-based
  triage heuristic, not physical severity, Pavement Condition Index, or an engineering
  maintenance recommendation. A qualified inspector must verify the site.</div>
  <footer>Generated from RoadWatch prediction metadata. Raw road imagery is not embedded in this report.</footer>
</body>
</html>"""
