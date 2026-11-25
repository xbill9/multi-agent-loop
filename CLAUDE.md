# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Workshop demo and codelab "Building a Multi-Agent System with ADK 2.0 and A2A" (an update of Google's codelab), presented at Pace University on 2026-12-02. Slides: Google Slides deck `1FVo8PcPUvdesq0asK6dQBcKdsSF0TGisCLlpe0v6C_w`.

## Commands

`make check` (lint + offline test: compile, codelab python blocks match `codelab-complete` via `scripts/check_codelab.py`, `docs/` matches a fresh claat export). Also `make docs`, `make run`, `make deploy`, `make install`, `make clean`.

## Codelab

- Source: `codelab/building-a-multi-agent-system-adk2.md` (claat markdown). `docs/` is generated and served by GitHub Pages at https://xbill9.github.io/multi-agent-loop/building-a-multi-agent-system-adk2/. Edit the markdown, then run `claat export -o docs codelab/building-a-multi-agent-system-adk2.md`; never hand-edit `docs/`.
- Code blocks in the codelab must match `codelab-complete/agents/*/agent.py` line for line. Change both together.
- Deck slides carry codelab step numbers in their chips, and QR codes link to `#<step-1>` anchors. Reordering or adding codelab steps means updating the deck.

## Layout rules

- `codelab-starter/` is what attendees fill in. Keep its `TODO`s; never put solution code there.
- `codelab-complete/` is the working demo. Both folders are vendored from `GoogleCloudPlatform/devrel-demos` (`agents/build-with-ai/production-ready-ai/`, Apache 2.0). Keep local edits small so `/sync-upstream` can reapply them.
- In each `agents/<name>/`, `adk_app.py` and `a2a_utils.py` are symlinks to `shared/`. Edit the file in `shared/`. `agents/orchestrator/authenticated_httpx.py` is a separate copy that differs from `shared/authenticated_httpx.py`.
- Every agent and `app/` has its own `pyproject.toml` and `uv.lock`; a dependency change touches each one that needs it.
- Runs on google-adk 2.x and a2a-sdk 1.x (upstream targets ADK 1.x / a2a-sdk 0.3). `shared/adk_app.py` mounts A2A itself at `/a2a/agent` via `_mount_a2a`, because ADK 2 would otherwise mount it under the folder name. `shared/a2a_utils.py` rewrites both `url` (0.3) and `supportedInterfaces[].url` (1.x) on served cards. Keep these when syncing upstream.

## Python and running

- No virtualenvs and no `uv run`/`uv sync` locally. Use the active `python3` (pyenv, currently 3.14.x) and `pip install` into it. Dockerfiles may keep using uv inside the container.
- `requires-python = ">=3.11"`: no upper cap, so the latest Python works. Keep the 3.11 floor, because the Docker build runs `uv sync`, which resolves for every allowed version, and fastapi 0.165 needs 3.11+.
- After any dependency change, run `uv lock` in each changed `pyproject.toml` directory (it only resolves and creates no venv) so Cloud Run builds get fresh locks.
- Keep packages on their latest releases and never downgrade; dependency pins are `>=` the installed latest. google-adk 2.15 declares `google-genai<3`, but the demo runs end to end with google-genai 3.6.1. In `requirements.txt` keep `google-genai>=2.34.0`, or a fresh install can't resolve.
- Agents need `a2a-sdk[http-server]` (it brings `sse-starlette`). This machine's shared Python hides missing extras, so before a deploy, build and start an agent image with docker to catch import errors.
- Attendees install with `python3 -m pip install -r requirements.txt` (in `codelab-starter/` and `codelab-complete/`); keep it in sync with the agent and app `pyproject.toml` files.
- Ports: researcher 8001, judge 8002, content builder 8003, orchestrator 8004, web app 8000. Agents start with `python3 adk_app.py --host 0.0.0.0 --port <port> --a2a .` from their own directory (the orchestrator runs without `--a2a`).
- Env: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `GOOGLE_GENAI_USE_VERTEXAI=true` (see `.env.example`). Model is hardcoded as `MODEL = "gemini-3-flash-preview"` in each `agent.py`.
- On Cloud Shell there is no ADC file, so the web app's Cloud Trace export fails with a quota-project 403. Start with `GOOGLE_CLOUD_QUOTA_PROJECT=<project> make run`. Findings from local runs are in `NOTES.md`.
- Agent cards locally: `http://localhost:800N/a2a/agent/.well-known/agent-card.json`. The orchestrator reads them from `RESEARCHER_AGENT_CARD_URL`, `JUDGE_AGENT_CARD_URL`, `CONTENT_BUILDER_AGENT_CARD_URL`; the web app needs `AGENT_SERVER_URL`.

## Lint

`ruff check` with the config in `codelab-complete/pyproject.toml`. Don't run `ruff format` over vendored files; it creates diffs against upstream.
