POETRY = poetry

.PHONY: setup test build wheel clean

setup: .venv/pyvenv.cfg

.venv/pyvenv.cfg: pyproject.toml
	$(POETRY) install --with dev
	@touch $@

test: setup
	$(POETRY) run pytest

build: setup
	$(POETRY) build

wheel: build

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
