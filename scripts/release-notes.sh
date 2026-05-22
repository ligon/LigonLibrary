#!/usr/bin/env bash
# scripts/release-notes.sh -- Scaffold CHANGELOG.md entries from git log.
#
# Collects commits since the most recent `v*` tag (or all commits if no
# tag exists yet) and inserts them as bullets under `## [Unreleased]` in
# CHANGELOG.md. Skips merge commits and "Bump version to ..." commits.
#
# The bullets are inserted verbatim from commit subjects -- review and
# reorganize them under Added / Changed / Fixed / Removed before
# releasing. Running the script twice will append a second batch, so
# re-runs are idempotent only if no new commits landed in between.
#
# Usage:
#   scripts/release-notes.sh            # uses ./CHANGELOG.md
#   scripts/release-notes.sh path/to/CHANGELOG.md
set -euo pipefail

CHANGELOG="${1:-CHANGELOG.md}"

if [ ! -f "$CHANGELOG" ]; then
    echo "error: $CHANGELOG not found" >&2
    exit 1
fi

if ! grep -q '^## \[Unreleased\]' "$CHANGELOG"; then
    echo "error: no '## [Unreleased]' heading in $CHANGELOG" >&2
    exit 1
fi

# Most recent vX.Y.Z tag, if any.
LAST_TAG="$(git tag --list 'v*' --sort=-v:refname | head -n 1 || true)"

if [ -n "$LAST_TAG" ]; then
    RANGE_ARGS=("${LAST_TAG}..HEAD")
    echo "Collecting commits in ${LAST_TAG}..HEAD" >&2
else
    RANGE_ARGS=()
    echo "No v* tag found; collecting all commits" >&2
fi

# --invert-grep + --grep filters out version-bump noise. --reverse so the
# oldest commit appears first under the heading.
BULLETS="$(
    git log \
        --no-merges \
        --reverse \
        --invert-grep --grep='^Bump version to' \
        --pretty=format:'- %s' \
        "${RANGE_ARGS[@]}"
)"

if [ -z "$BULLETS" ]; then
    echo "No new commits since ${LAST_TAG:-repo start}." >&2
    exit 0
fi

COUNT="$(printf '%s\n' "$BULLETS" | wc -l | tr -d ' ')"

# Insert the bullets immediately after `## [Unreleased]`.
TMP="$(mktemp)"
awk -v bullets="$BULLETS" '
    !done && /^## \[Unreleased\]/ {
        print
        print ""
        print bullets
        done = 1
        next
    }
    { print }
' "$CHANGELOG" > "$TMP"

mv "$TMP" "$CHANGELOG"
echo "Inserted ${COUNT} bullet(s) under [Unreleased] in ${CHANGELOG}." >&2
echo "Review and reorganize under Added / Changed / Fixed before releasing." >&2
