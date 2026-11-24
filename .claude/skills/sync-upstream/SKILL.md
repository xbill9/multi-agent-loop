---
name: sync-upstream
description: Refresh codelab-starter/ and codelab-complete/ from GoogleCloudPlatform/devrel-demos, show what changed upstream, and reapply this repo's local changes. Use when asked to update, sync or refresh the codelab code.
disable-model-invocation: true
---

1. Sparse-clone upstream into the scratchpad:
   ```
   git clone --depth 1 --filter=blob:none --sparse https://github.com/GoogleCloudPlatform/devrel-demos.git <scratch>/devrel
   git -C <scratch>/devrel sparse-checkout set agents/build-with-ai/production-ready-ai
   ```
2. `diff -r` each upstream folder (`prai-roadshow-lab-1-starter`, `prai-roadshow-lab-1-complete`) against `codelab-starter/` and `codelab-complete/`. Summarize upstream changes separately from this repo's local changes.
3. Local changes to keep:
   - `requires-python` without the `<3.14` cap in every `pyproject.toml`
   - `run_local.sh` starts processes with `python3`, not `uv run`
   - dependency pins `>=` the latest installed versions (google-adk 2.x, a2a-sdk 1.x)
   - `shared/adk_app.py` `_mount_a2a` (A2A at `/a2a/agent`) and the card URL rewrite in `shared/a2a_utils.py`
   - anything else shown in `git log -p -- codelab-starter codelab-complete` after the initial import
4. Copy upstream over the folders (preserve the `shared/` symlinks with `cp -a`), reapply the local changes, and show `git diff --stat`.
5. Do not commit until the user has reviewed the diff. Run `/run-demo` afterwards if the user wants it checked.
