# Deployment guide

## Prerequisites

- Docker Engine with Compose v2
- A trained RDD2022-compatible checkpoint at `models/best.pt`
- At least 4 GB RAM for the small model; GPU deployment requires a compatible container
  runtime and matching PyTorch/CUDA environment

## Production-like local stack

```bash
cp .env.example .env
export POSTGRES_PASSWORD='replace-with-a-strong-local-secret'
docker compose up --build -d
docker compose ps
```

Services:

| Service | Local URL | Purpose |
|---|---|---|
| Dashboard | <http://localhost:8501> | Inspector interface and map |
| API | <http://localhost:8000> | Inference and inspection resources |
| API docs | <http://localhost:8000/docs> | OpenAPI interface |
| PostgreSQL | internal only | Prediction metadata |

## Model configuration

The compose file mounts `./models` read-only and expects `/app/models/best.pt`. To use a GPU:

```bash
export ROADWATCH_MODEL_DEVICE=0
docker compose up --build -d
```

GPU use also requires adding the relevant Compose device reservation and using a
CUDA-compatible API image. Do not set device `0` on a CPU-only image.

## Readiness verification

```bash
curl --fail http://localhost:8000/health/live
curl --fail http://localhost:8000/health/ready
curl --fail http://localhost:8501/_stcore/health
```

If liveness passes but readiness returns 503, inspect the `detail` field. The common causes
are a missing checkpoint, the ML extra not being installed, or an incompatible checkpoint.

## Configuration reference

All variables have the `ROADWATCH_` prefix.

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `test`, or `production` |
| `DATABASE_URL` | SQLite file | Use `postgresql+psycopg://...` for PostgreSQL |
| `MODEL_PATH` | `models/best.pt` | RDD2022-compatible checkpoint |
| `MODEL_DEVICE` | `cpu` | `cpu`, CUDA index such as `0`, or supported accelerator |
| `CONFIDENCE_THRESHOLD` | `0.35` | Detection confidence threshold |
| `IOU_THRESHOLD` | `0.45` | Non-maximum suppression IoU threshold |
| `MAX_UPLOAD_MB` | `15` | Bounded from 1 to 100 MB |
| `CORS_ORIGINS` | local dashboard | JSON array of allowed origins |

## Production checklist

- Store secrets in the deployment platform, not `.env` committed to Git.
- Put TLS and authentication in front of the API.
- Pin and sign the approved model artifact; record its dataset and metrics.
- Back up PostgreSQL and define data retention.
- Set CPU, memory, request-size, and concurrency limits.
- Send metrics and structured logs to monitored systems.
- Run a Qatar-specific acceptance test before operational use.
- Document the human verification and escalation workflow.

## Updating a model

1. Train and evaluate the candidate using the documented data split.
2. Compare per-class AP, false negatives, calibration, and Qatar acceptance slices.
3. Update `docs/model-card.md` with measured values and provenance.
4. Export and scan the artifact.
5. Replace the checkpoint through an immutable versioned release.
6. Deploy to a non-production environment and run smoke tests.
7. Promote only after human approval.

