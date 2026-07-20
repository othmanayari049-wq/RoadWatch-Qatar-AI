# API guide

The service publishes interactive OpenAPI documentation at `/docs` and ReDoc at `/redoc`.
All operational resources use the `/api/v1` prefix.

## Health

```http
GET /health/live
GET /health/ready
```

Liveness does not require model weights. Readiness returns `503 Service Unavailable` until
the configured road-damage checkpoint is loaded.

## Create a prediction

```http
POST /api/v1/predictions
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `image` | file | yes | JPEG, PNG, or WebP road image |
| `latitude` | float | no | WGS84 latitude; must accompany longitude |
| `longitude` | float | no | WGS84 longitude; must accompany latitude |
| `persist` | boolean | no | Store prediction metadata; defaults to `true` |

Example:

```bash
curl --fail-with-body \
  -X POST http://localhost:8000/api/v1/predictions \
  -F image=@road.jpg \
  -F latitude=25.2854 \
  -F longitude=51.5310 \
  -F persist=true
```

Successful response:

```json
{
  "source_filename": "road.jpg",
  "prediction": {
    "id": "8f6bf38c-83ab-4d29-866c-33378b2c262b",
    "created_at": "2026-07-20T08:00:00Z",
    "model_version": "best",
    "image_width": 1920,
    "image_height": 1080,
    "inference_ms": 31.7,
    "detections": [
      {
        "damage_class": "D40",
        "label": "Pothole",
        "confidence": 0.91,
        "bbox": {"x1": 604, "y1": 431, "x2": 945, "y2": 719},
        "area_ratio": 0.047,
        "severity_score": 77.4,
        "severity": "high"
      }
    ],
    "location": {"latitude": 25.2854, "longitude": 51.531}
  }
}
```

The response above illustrates the schema; it is not a claimed model result.

## Inspection resources

```http
GET /api/v1/inspections?limit=50&offset=0
GET /api/v1/inspections/{inspection_id}
GET /api/v1/inspections/{inspection_id}/report
GET /api/v1/analytics/summary
```

Pagination accepts a limit from 1 to 200 and a non-negative offset. The summary returns
inspection count, detection count, geotagged count, average inference time, class counts,
and severity counts.

The report endpoint downloads a self-contained, printable HTML report containing prediction
metadata, location, detections, boxes, scores, and the responsible-use notice. Raw imagery is
not embedded.

## Metrics

```http
GET /metrics
```

The Prometheus endpoint includes request count, request duration, and successful prediction
count. Route templates—not raw URLs—are used as metric labels to avoid unbounded UUID label
cardinality.

## Error behavior

| Status | Meaning |
|---:|---|
| 400 | Invalid or unsupported image |
| 404 | Inspection identifier not found |
| 422 | Invalid form or pagination values |
| 503 | Trained model is unavailable |

Every HTTP response includes `X-Request-ID`. Clients may provide their own value through the
same header for request correlation.
