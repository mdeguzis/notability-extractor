# Makefile for notability-extractor
# Run `make help` to list targets.

.DEFAULT_GOAL := help
SHELL := bash

# pass CLI args through: make run ARGS="--list-tables"
ARGS ?=

.PHONY: help install lock lint typecheck format format-check \
        test test-cov build run clean check

help: ## show this help
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} \
	      /^[a-zA-Z_-]+:.*?##/ { printf "  %-14s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## install dev env + put notability-extractor on PATH (~/.local/bin)
	uv sync
	uv tool install --editable --force .

lock: ## regenerate uv.lock
	uv lock

lint: ## run ruff check then pylint on src and tests
	uv run ruff check src tests
	uv run pylint src tests

typecheck: ## run mypy then pyright on src
	uv run mypy src
	uv run pyright

format: ## run black then autopep8 (writes changes in place)
	uv run black src tests
	uv run autopep8 --in-place --recursive src tests

format-check: ## verify formatting without writing
	uv run black --check src tests
	@diff_out=$$(uv run autopep8 --diff --recursive src tests); \
	if [ -n "$$diff_out" ]; then \
		echo "$$diff_out"; \
		echo "autopep8 would make changes - run 'make format'"; \
		exit 1; \
	fi

test: ## run pytest
	uv run pytest

test-cov: ## run pytest with coverage report
	uv run pytest --cov --cov-report=term-missing

build: ## build wheel and sdist into dist/
	uv build

run: ## run the CLI - pass args via ARGS="..."
	uv run notability-extractor $(ARGS)

clean: ## remove build artifacts and tool caches
	rm -rf build/ dist/ *.egg-info src/*.egg-info \
	       .pytest_cache .coverage htmlcov/ \
	       .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

check: lint typecheck format-check test ## full gate: lint + typecheck + format-check + test
