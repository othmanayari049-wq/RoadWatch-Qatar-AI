.DEFAULT_GOAL := help
.PHONY: help install install-all format lint typecheck test check api dashboard train docker-up docker-down

PYTHON ?= python

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "RoadWatch Qatar AI commands:\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install API and development dependencies
	$(PYTHON) -m pip install -e '.[dev]'

install-all: ## Install API, ML, dashboard, deployment, and development dependencies
	$(PYTHON) -m pip install -e '.[ml,dashboard,deploy,dev]'

format: ## Format source and tests
	ruff format .
	ruff check --fix .

lint: ## Run Ruff linting and formatting checks
	ruff check .
	ruff format --check .

typecheck: ## Run strict type checks on the service layers
	mypy src/roadwatch --exclude 'dashboard/app.py'

test: ## Run tests with branch coverage
	pytest --cov=roadwatch --cov-report=term-missing --cov-report=xml

check: lint typecheck test ## Run the complete local quality gate

api: ## Start the API with reload
	roadwatch serve --reload

dashboard: ## Start the Streamlit dashboard
	streamlit run src/roadwatch/dashboard/app.py

train: ## Train the default detector configuration
	$(PYTHON) scripts/train.py

docker-up: ## Build and run the production-like stack
	docker compose up --build

docker-down: ## Stop the stack
	docker compose down

