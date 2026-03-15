POETRY = poetry

.PHONY: setup test build wheel clean release

setup: .venv/pyvenv.cfg

.venv/pyvenv.cfg: pyproject.toml
	$(POETRY) install --with dev
	@touch $@

test: setup
	$(POETRY) run pytest

build: setup
	$(POETRY) build

wheel: build

# Usage: make release BUMP=patch  (or minor, major, prepatch, etc.)
BUMP ?= patch
release: build
	$(eval NEW_VER := $(shell $(POETRY) version $(BUMP) -s))
	git add pyproject.toml
	git commit -m "Bump version to $(NEW_VER)"
	git tag v$(NEW_VER)
	@echo "Tagged v$(NEW_VER). Run 'git push && git push --tags' to publish."

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
