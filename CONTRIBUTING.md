# Contributing

Contributions that improve reproducibility, safety, Qatar-domain evaluation, accessibility,
or system quality are welcome.

## Development setup

```bash
git clone https://github.com/othmanayari049-wq/RoadWatch-Qatar-AI.git
cd RoadWatch-Qatar-AI
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[ml,dashboard,deploy,dev]'
pre-commit install
make check
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`.

## Pull requests

- Create a focused branch from `main`.
- Add or update tests for behavioral changes.
- Keep the public API backward compatible or document the versioning decision.
- Run `make check` before opening a pull request.
- Explain the problem, approach, user impact, validation, and limitations.
- Do not commit datasets, road images, secrets, database files, model weights, or generated
  training runs.
- Do not report model metrics without a reproducible artifact, split, and evaluation command.

## Commit style

Use short, imperative conventional prefixes when practical:

- `feat:` user-visible capability
- `fix:` defect correction
- `test:` test-only change
- `docs:` documentation
- `ci:` automation or deployment
- `refactor:` behavior-preserving code improvement

## Adding a model

A model contribution must include:

- data provenance and license;
- group/geographic split method;
- complete training configuration and seed;
- artifact digest;
- per-class evaluation and error analysis;
- latency hardware and measurement method;
- updated data and model cards;
- confirmation that model files are excluded from ordinary Git history.

## Reporting security issues

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).

