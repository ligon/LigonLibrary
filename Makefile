POETRY = poetry

.PHONY: setup test build wheel check publish clean release release-notes

setup: .venv/pyvenv.cfg

.venv/pyvenv.cfg: pyproject.toml
	$(POETRY) install --with dev
	@touch $@

test: setup
	$(POETRY) run pytest

build: setup
	rm -rf dist/
	$(POETRY) build

wheel: build

check: build
	$(POETRY) run python -m pip install --quiet --upgrade twine
	$(POETRY) run twine check dist/*

publish: check
	$(POETRY) publish

# Scaffold a new CHANGELOG.md section from commits since the last v* tag.
# Bullets land under `## [Unreleased]` for you to organize before releasing.
release-notes:
	@./scripts/release-notes.sh CHANGELOG.md

# Usage: make release BUMP=patch   (or minor, major, prepatch, etc.)
# Bumps the version, commits pyproject.toml + CHANGELOG.md, and tags.
# Push the tag to trigger the Release workflow:
#   git push && git push --tags
BUMP ?= patch
release: setup
	$(eval NEW_VER := $(shell $(POETRY) version $(BUMP) -s))
	@echo "Releasing v$(NEW_VER)"
	$(MAKE) check
	git add pyproject.toml CHANGELOG.md 2>/dev/null || git add pyproject.toml
	git commit -m "Bump version to $(NEW_VER)"
	git tag -a v$(NEW_VER) -m "Release v$(NEW_VER)"
	@echo
	@echo "Tagged v$(NEW_VER)."
	@echo "Next: git push && git push --tags"
	@echo "(The Release workflow will build and publish to PyPI on tag push.)"

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
