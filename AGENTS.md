# gitlab-artifact-cleaner

Single-file Python utility for deleting expired or unwanted GitLab job artifacts.

## Verify

`mise run check`: create a uv environment, install both requirements files, run Ruff and isort.

CI uses the same command plus actionlint, zizmor, and strict Renovate validation. The required gate is `check`.

## Stack

Follows https://github.com/BlackDark/agent-presets/blob/main/stack/core.md. This repo intentionally stays a small requirements-based script; no pyproject migration is needed.

## Map

- `gitlab_artifact_cleaner.py`: CLI and cleanup logic.
- `requirements.txt`: runtime dependencies.
- `requirements.dev.txt`: lint tools.

## Git

- Conventional Commits, one topic per PR.
- Squash unless commits need separate review.
- Force-push only with `--force-with-lease` on own branches.

## Boundaries

- Tools come from `mise.toml`; no global installs.
- Never use a personal GitLab token or run deletion against a real project from a local session.
