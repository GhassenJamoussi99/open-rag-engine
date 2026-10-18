.DEFAULT_GOAL := help
.PHONY: help install lint format typecheck test check clean

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-10s %s\n", $$1, $$2}'

install: ## Install dependencies and git hooks
	uv sync
	uv run pre-commit install

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-fix lint issues and format code
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Run mypy in strict mode
	uv run mypy

test: ## Run tests with coverage
	uv run pytest --cov --cov-report=term-missing

check: lint typecheck test ## Run every quality gate

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build
