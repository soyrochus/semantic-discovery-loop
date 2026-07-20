#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
OUTPUT_DIR=${1:-"$REPO_ROOT/dist"}
VERSION=${VERSION:-$(date +%Y%m%d)}
PACKAGE_NAME="semantic-discovery-loop-installer-${VERSION}"
STAGING_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/semantic-discovery-loop-installer.XXXXXX")
STAGING_DIR="$STAGING_ROOT/$PACKAGE_NAME"

cleanup() {
  rm -rf "$STAGING_ROOT"
}

trap cleanup EXIT INT TERM HUP

mkdir -p "$STAGING_DIR/resources" "$OUTPUT_DIR"

cp "$SCRIPT_DIR/install.sh" "$STAGING_DIR/install.sh"
chmod 755 "$STAGING_DIR/install.sh"

cp -R "$REPO_ROOT/.agent-loop" "$STAGING_DIR/resources/.agent-loop"
mkdir -p "$STAGING_DIR/resources/.github/prompts"
cp "$REPO_ROOT/.github/prompts/run-semantic-discovery-loop.prompt.md" "$STAGING_DIR/resources/.github/prompts/run-semantic-discovery-loop.prompt.md"
mkdir -p "$STAGING_DIR/resources/.claude/skills/semantic-discovery-loop"
cp "$REPO_ROOT/.claude/skills/semantic-discovery-loop/SKILL.md" "$STAGING_DIR/resources/.claude/skills/semantic-discovery-loop/SKILL.md"
cp "$SCRIPT_DIR/templates/AGENTS.md" "$STAGING_DIR/resources/AGENTS.md"
mkdir -p "$STAGING_DIR/resources/.github"
cp "$SCRIPT_DIR/templates/copilot-instructions.md" "$STAGING_DIR/resources/.github/copilot-instructions.md"
cp "$SCRIPT_DIR/README.md" "$STAGING_DIR/README.md"

ARCHIVE_PATH="$OUTPUT_DIR/$PACKAGE_NAME.zip"
rm -f "$ARCHIVE_PATH"

if command -v zip >/dev/null 2>&1; then
  (
    cd "$STAGING_ROOT"
    zip -qr "$ARCHIVE_PATH" "$PACKAGE_NAME"
  )
elif command -v ditto >/dev/null 2>&1; then
  ditto -c -k --sequesterRsrc --keepParent "$STAGING_DIR" "$ARCHIVE_PATH"
else
  echo "error: neither zip nor ditto is available" >&2
  exit 1
fi

echo "Created $ARCHIVE_PATH"