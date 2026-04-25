UV ?= uv

.PHONY: install lint type-check test test-cov build clean pre-commit-install pre-commit-run

install:
	$(UV) sync --extra dev

lint:
	$(UV) run ruff check src tests

type-check:
	$(UV) run mypy src/contract_graph

test:
	$(UV) run pytest tests -q

test-cov:
	$(UV) run pytest tests --cov=contract_graph --cov-report=term-missing --cov-report=xml

build:
	$(UV) build

clean:
	$(UV) run python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ('.mypy_cache','.pytest_cache','.ruff_cache','dist','build')]; [f.unlink() for f in pathlib.Path('.').glob('.coverage*') if f.is_file()]"

pre-commit-install:
	$(UV) tool run pre-commit install
	$(UV) tool run pre-commit install --hook-type pre-push

pre-commit-run:
	$(UV) tool run pre-commit run --all-files
