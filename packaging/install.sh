#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage: ./install.sh --target /path/to/repository [--project-name NAME] [--copilot] [--claude] [--codex] [--all] [--force]

Installs the semantic discovery loop into an existing repository.

Options:
  --target PATH   Repository root to install into.
  --project-name  Friendly repository name to insert into template files.
  --copilot       Install GitHub Copilot adapter files.
  --claude        Install Claude Code adapter files.
  --codex         Install Codex adapter file.
  --all           Install all supported adapters. This is the default.
  --force         Overwrite existing files without creating backups.
  --help          Show this help text.
EOF
}

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RESOURCE_ROOT="$SCRIPT_DIR/resources"
CORE_ROOT=
PROMPT_ROOT=
CLAUDE_ROOT=
COPILOT_TEMPLATE=
CODEX_TEMPLATE=
TARGET_DIR=
PROJECT_NAME=
INSTALL_COPILOT=1
INSTALL_CLAUDE=1
INSTALL_CODEX=1
FORCE=0
SELECTED_ADAPTER=0
BACKUP_DIR=

if [ -d "$RESOURCE_ROOT/.agent-loop" ]; then
  CORE_ROOT="$RESOURCE_ROOT"
  PROMPT_ROOT="$RESOURCE_ROOT"
  CLAUDE_ROOT="$RESOURCE_ROOT"
  COPILOT_TEMPLATE="$RESOURCE_ROOT/.github/copilot-instructions.md"
  CODEX_TEMPLATE="$RESOURCE_ROOT/AGENTS.md"
else
  RESOURCE_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
  CORE_ROOT="$RESOURCE_ROOT"
  PROMPT_ROOT="$RESOURCE_ROOT"
  CLAUDE_ROOT="$RESOURCE_ROOT"
  COPILOT_TEMPLATE="$SCRIPT_DIR/templates/copilot-instructions.md"
  CODEX_TEMPLATE="$SCRIPT_DIR/templates/AGENTS.md"
fi

infer_project_name() {
  basename "$TARGET_DIR"
}

render_template() {
  source_path=$1
  destination_path=$2

  sed "s|{{PROJECT_NAME}}|$PROJECT_NAME|g" "$source_path" > "$destination_path"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || { echo "error: --target requires a path" >&2; exit 1; }
      TARGET_DIR=$2
      shift 2
      ;;
    --project-name)
      [ "$#" -ge 2 ] || { echo "error: --project-name requires a value" >&2; exit 1; }
      PROJECT_NAME=$2
      shift 2
      ;;
    --copilot)
      if [ "$SELECTED_ADAPTER" -eq 0 ]; then
        INSTALL_COPILOT=0
        INSTALL_CLAUDE=0
        INSTALL_CODEX=0
        SELECTED_ADAPTER=1
      fi
      INSTALL_COPILOT=1
      shift
      ;;
    --claude)
      if [ "$SELECTED_ADAPTER" -eq 0 ]; then
        INSTALL_COPILOT=0
        INSTALL_CLAUDE=0
        INSTALL_CODEX=0
        SELECTED_ADAPTER=1
      fi
      INSTALL_CLAUDE=1
      shift
      ;;
    --codex)
      if [ "$SELECTED_ADAPTER" -eq 0 ]; then
        INSTALL_COPILOT=0
        INSTALL_CLAUDE=0
        INSTALL_CODEX=0
        SELECTED_ADAPTER=1
      fi
      INSTALL_CODEX=1
      shift
      ;;
    --all)
      INSTALL_COPILOT=1
      INSTALL_CLAUDE=1
      INSTALL_CODEX=1
      SELECTED_ADAPTER=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

[ -n "$TARGET_DIR" ] || { echo "error: --target is required" >&2; usage >&2; exit 1; }
[ -d "$TARGET_DIR" ] || { echo "error: target directory does not exist: $TARGET_DIR" >&2; exit 1; }
[ -d "$CORE_ROOT/.agent-loop" ] || { echo "error: installer resources are missing" >&2; exit 1; }
[ -f "$COPILOT_TEMPLATE" ] || { echo "error: Copilot template is missing" >&2; exit 1; }
[ -f "$CODEX_TEMPLATE" ] || { echo "error: Codex template is missing" >&2; exit 1; }
[ -n "$PROJECT_NAME" ] || PROJECT_NAME=$(infer_project_name)

backup_path() {
  src=$1
  rel=$2

  if [ "$FORCE" -eq 1 ]; then
    rm -rf "$src"
    return
  fi

  if [ -z "$BACKUP_DIR" ]; then
    timestamp=$(date +%Y%m%d-%H%M%S)
    BACKUP_DIR="$TARGET_DIR/.semantic-discovery-loop-backups/$timestamp"
    mkdir -p "$BACKUP_DIR"
  fi

  mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
  mv "$src" "$BACKUP_DIR/$rel"
}

copy_entry() {
  source_path=$1
  relative_path=$2
  destination_path="$TARGET_DIR/$relative_path"

  if [ -e "$destination_path" ] || [ -L "$destination_path" ]; then
    backup_path "$destination_path" "$relative_path"
  fi

  mkdir -p "$(dirname "$destination_path")"

  if [ -d "$source_path" ]; then
    cp -R "$source_path" "$destination_path"
  else
    cp "$source_path" "$destination_path"
  fi
}

copy_template() {
  source_path=$1
  relative_path=$2
  destination_path="$TARGET_DIR/$relative_path"

  if [ -e "$destination_path" ] || [ -L "$destination_path" ]; then
    backup_path "$destination_path" "$relative_path"
  fi

  mkdir -p "$(dirname "$destination_path")"
  render_template "$source_path" "$destination_path"
}

copy_entry "$CORE_ROOT/.agent-loop" ".agent-loop"

if [ "$INSTALL_COPILOT" -eq 1 ]; then
  copy_entry "$PROMPT_ROOT/.github/prompts/run-semantic-discovery-loop.prompt.md" ".github/prompts/run-semantic-discovery-loop.prompt.md"
  copy_template "$COPILOT_TEMPLATE" ".github/copilot-instructions.md"
fi

if [ "$INSTALL_CLAUDE" -eq 1 ]; then
  copy_entry "$CLAUDE_ROOT/.claude/skills/semantic-discovery-loop" ".claude/skills/semantic-discovery-loop"
fi

if [ "$INSTALL_CODEX" -eq 1 ]; then
  copy_template "$CODEX_TEMPLATE" "AGENTS.md"
fi

echo "Installed semantic-discovery-loop into $TARGET_DIR"

if [ -n "$BACKUP_DIR" ]; then
  echo "Backed up replaced files to $BACKUP_DIR"
fi