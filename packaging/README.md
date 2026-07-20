# Semantic Discovery Loop Installer

This directory contains a portable installer bundle for the semantic discovery loop.

## What gets packaged

- `.agent-loop/` — the assistant-neutral loop core
- `.github/prompts/run-semantic-discovery-loop.prompt.md` — GitHub Copilot prompt
- `.github/copilot-instructions.md` — generic Copilot repo instructions for the loop
- `.claude/skills/semantic-discovery-loop/SKILL.md` — Claude Code skill
- `AGENTS.md` — generic Codex/agent entrypoint
- `install.sh` — portable installer for macOS and Linux

## Build the zip bundle

Run from the repository root:

```sh
./packaging/build-installer.sh
```

The zip archive is written to `dist/` by default.

To choose a different output directory:

```sh
./packaging/build-installer.sh /absolute/path/to/output
```

## Use the installer

Unzip the generated archive, then run:

```sh
./install.sh --target /path/to/target-repository
```

To brand the installed Copilot and Codex instructions with a friendly repository name:

```sh
./install.sh --target /path/to/target-repository --project-name my-app
```

Supported adapter flags:

```sh
./install.sh --target /path/to/target-repository --copilot
./install.sh --target /path/to/target-repository --claude
./install.sh --target /path/to/target-repository --codex
./install.sh --target /path/to/target-repository --all
```

By default the installer copies the loop core plus all three adapters.

If `--project-name` is omitted, the installer uses the target directory name.

If a target file already exists, the installer moves it into
`.semantic-discovery-loop-backups/<timestamp>/` inside the target repository. Use
`--force` to overwrite without backups.