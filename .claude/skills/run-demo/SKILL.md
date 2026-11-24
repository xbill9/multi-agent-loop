---
name: run-demo
description: Start the multi-agent course-creator demo locally (four agents plus web app) with the active python3, verify each A2A agent card, and send one test prompt end to end. Use when asked to run, start, test or smoke-test the demo.
---

Run from `codelab-complete/`. No virtualenvs and no `uv run`: use the active `python3`.

1. Environment: `GOOGLE_CLOUD_PROJECT` must be set (default `gcloud config get-value project`), plus `GOOGLE_CLOUD_LOCATION=global` and `GOOGLE_GENAI_USE_VERTEXAI=true`. If ADC is missing, ask the user to run `! gcloud auth application-default login`.
2. Dependencies: `python3 -m pip install` the dependencies listed in each `agents/*/pyproject.toml` and `app/pyproject.toml` if imports fail. Report any package that has no build for the current Python version rather than downgrading Python.
3. Start with `./run_local.sh` in the background (it frees ports 8000-8004 first). Wait for the ports to listen.
4. Check each card returns JSON:
   `curl -sf http://localhost:800N/a2a/agent/.well-known/agent-card.json` for N = 1, 2, 3.
5. End to end:
   ```
   curl -sN -X POST http://localhost:8000/api/chat_stream \
     -H 'Content-Type: application/json' \
     -d '{"message": "Create a short course about the history of coffee", "user_id": "demo"}'
   ```
   Pass when the stream ends with a Markdown course that has a `#` title and `##` sections.
6. Report what passed and failed with the exact error text. Stop the processes when done unless the user wants them left running.
