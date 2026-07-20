"""Streamlit operations dashboard for RoadWatch Qatar AI."""

from __future__ import annotations

import os
from io import BytesIO

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from PIL import Image

from roadwatch.dashboard.client import DashboardAPIError, RoadWatchClient
from roadwatch.domain.models import DamageClass, Severity, StoredInspection
from roadwatch.services.image_io import annotate_image

SEVERITY_COLORS = {
    Severity.LOW: [22, 163, 74, 190],
    Severity.MEDIUM: [245, 158, 11, 210],
    Severity.HIGH: [220, 38, 38, 220],
}

st.set_page_config(
    page_title="RoadWatch Qatar AI",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1500px;}
      [data-testid="stMetric"] {background: #f8fafc; border: 1px solid #e2e8f0;
        padding: 1rem; border-radius: 0.75rem;}
      .disclaimer {padding: .8rem 1rem; border-left: 4px solid #f59e0b;
        background: #fffbeb; border-radius: .25rem; color: #78350f;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def api_client(base_url: str) -> RoadWatchClient:
    return RoadWatchClient(base_url)


def severity_label(record: StoredInspection) -> str:
    maximum = record.prediction.maximum_severity
    return maximum.value if maximum else "none"


def render_header() -> None:
    left, right = st.columns([4, 1])
    with left:
        st.title("RoadWatch Qatar AI")
        st.caption("AI-assisted road inspection and geospatial defect triage")
    with right:
        st.markdown("**RDD2022 classes**  ·  D00  ·  D10  ·  D20  ·  D40")


def render_detection(client: RoadWatchClient) -> None:
    st.subheader("Inspect a road image")
    uploaded = st.file_uploader(
        "Upload a clear road image",
        type=["jpg", "jpeg", "png", "webp"],
        help="Images are analyzed in memory. Raw image bytes are not stored by the API.",
    )
    left, right, privacy = st.columns([1, 1, 2])
    with left:
        latitude = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=25.2854)
    with right:
        longitude = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=51.5310)
    with privacy:
        include_location = st.checkbox("Attach location", value=True)
        persist = st.checkbox("Save result metadata", value=True)

    if uploaded is None:
        st.info("Upload a JPEG, PNG, or WebP image to begin.")
        return

    source_bytes = uploaded.getvalue()
    source = Image.open(BytesIO(source_bytes)).convert("RGB")
    preview, result_column = st.columns(2)
    with preview:
        st.image(source, caption="Input image", use_container_width=True)

    if st.button("Run inspection", type="primary", use_container_width=True):
        with st.spinner("Analyzing visible road damage…"):
            try:
                record = client.predict(
                    filename=uploaded.name,
                    data=source_bytes,
                    content_type=uploaded.type or "image/jpeg",
                    latitude=latitude if include_location else None,
                    longitude=longitude if include_location else None,
                    persist=persist,
                )
            except DashboardAPIError as exc:
                st.error(str(exc))
                return
        st.session_state["latest_prediction"] = record

    record = st.session_state.get("latest_prediction")
    if not isinstance(record, StoredInspection):
        return
    with result_column:
        annotated = annotate_image(source, record.prediction)
        st.image(annotated, caption="AI-assisted detections", use_container_width=True)

    prediction = record.prediction
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Detections", len(prediction.detections))
    m2.metric("Maximum severity", severity_label(record).title())
    m3.metric("Inference", f"{prediction.inference_ms:.1f} ms")
    m4.metric("Model", prediction.model_version)

    if prediction.detections:
        rows = [
            {
                "Class": item.damage_class.value,
                "Damage": item.label,
                "Confidence": round(item.confidence * 100, 1),
                "Visible area (%)": round(item.area_ratio * 100, 2),
                "Priority score": item.severity_score,
                "Priority": item.severity.value.title(),
            }
            for item in prediction.detections
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.success("No supported road-damage classes were detected above the threshold.")


def render_map(client: RoadWatchClient) -> None:
    st.subheader("Geospatial inspection map")
    try:
        records = client.inspections()
    except DashboardAPIError as exc:
        st.error(str(exc))
        return

    points = []
    for record in records:
        prediction = record.prediction
        if prediction.location is None:
            continue
        maximum = prediction.maximum_severity or Severity.LOW
        points.append(
            {
                "latitude": prediction.location.latitude,
                "longitude": prediction.location.longitude,
                "severity": maximum.value.title(),
                "color": SEVERITY_COLORS[maximum],
                "detections": len(prediction.detections),
                "file": record.source_filename,
            }
        )
    if not points:
        st.info("No geotagged inspections are available yet.")
        return

    dataframe = pd.DataFrame(points)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=dataframe,
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius=45,
        pickable=True,
        stroked=True,
        get_line_color=[255, 255, 255],
    )
    view = pdk.ViewState(
        latitude=float(dataframe["latitude"].mean()),
        longitude=float(dataframe["longitude"].mean()),
        zoom=11,
    )
    tooltip = {"html": "<b>{file}</b><br/>Priority: {severity}<br/>Detections: {detections}"}
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))


def render_analytics(client: RoadWatchClient) -> None:
    st.subheader("Inspection analytics")
    try:
        summary = client.summary()
    except DashboardAPIError as exc:
        st.error(str(exc))
        return

    a, b, c, d = st.columns(4)
    a.metric("Inspections", summary.total_inspections)
    b.metric("Detections", summary.total_detections)
    c.metric("Geotagged", summary.geotagged_inspections)
    d.metric("Average inference", f"{summary.average_inference_ms:.1f} ms")

    class_names = {item: item.display_name for item in DamageClass}
    classes = pd.DataFrame(
        [
            {"Damage": class_names[key], "Count": value}
            for key, value in summary.damage_class_counts.items()
        ]
    )
    severities = pd.DataFrame(
        [
            {"Priority": key.value.title(), "Count": value}
            for key, value in summary.severity_counts.items()
        ]
    )
    left, right = st.columns(2)
    with left:
        chart = px.bar(
            classes,
            x="Damage",
            y="Count",
            title="Detections by damage class",
            color="Damage",
        )
        st.plotly_chart(chart, use_container_width=True)
    with right:
        chart = px.pie(
            severities,
            names="Priority",
            values="Count",
            title="Inspection priority distribution",
            color="Priority",
            color_discrete_map={"Low": "#16A34A", "Medium": "#F59E0B", "High": "#DC2626"},
        )
        st.plotly_chart(chart, use_container_width=True)


def render_methodology() -> None:
    st.subheader("Methodology and responsible use")
    st.markdown(
        """
        - The detector is trained for four RDD2022 classes: D00, D10, D20, and D40.
        - Confidence, visible image area, and a documented class prior produce a transparent
          inspection-priority score.
        - Priority is not the same as physical crack depth, pavement condition index, or a
          certified civil-engineering assessment.
        - Qatar deployment requires a locally collected, consented test set covering glare,
          dust, shadows, road markings, night scenes, and different camera heights.
        - Raw uploaded images are not persisted by the reference API. Only prediction metadata
          is stored when the operator selects that option.
        """
    )
    st.markdown(
        '<div class="disclaimer"><b>Decision-support only.</b> A qualified road engineer '
        "must verify defects before maintenance decisions are made.</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    render_header()
    api_url = st.sidebar.text_input(
        "API URL", value=os.getenv("ROADWATCH_API_URL", "http://localhost:8000")
    )
    client = api_client(api_url)
    ready, detail = client.readiness()
    if ready:
        st.sidebar.success(f"API ready · {detail}")
    else:
        st.sidebar.error(detail)
    st.sidebar.caption("Model output is inspection support, not an engineering certification.")

    detect, map_tab, analytics, methodology = st.tabs(
        ["New inspection", "Inspection map", "Analytics", "Methodology"]
    )
    with detect:
        render_detection(client)
    with map_tab:
        render_map(client)
    with analytics:
        render_analytics(client)
    with methodology:
        render_methodology()


if __name__ == "__main__":
    main()
