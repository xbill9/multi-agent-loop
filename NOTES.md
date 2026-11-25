# Notes

Findings from running the demo locally. Newest first.

## 2026-11-25: end-to-end run on Cloud Shell

Setup: `codelab-complete` started with `make run` against project `aisprint-491218`, google-adk 2.15.1, system Python 3.12.3 (Ubuntu 24.04). Requests sent to the web app at `POST localhost:8000/api/chat_stream`.

### The loop works

One request runs researcher → judge → content builder and streams a result. Timings from one run: researcher 0–11 s, judge 11–15 s, content builder 16–31 s, 31 s in total. The judge passed the research on the first round in all three runs.

### The web app returns every agent's text, twice

`app/main.py:192-195` joins the text of every event from every author. Each remote agent's reply reaches the orchestrator twice over A2A: first as an in-progress update with `thought: true`, then as the final message with the same text. Events seen from `localhost:8004/run_sse` for one request:

| Event | Author | Text |
|---|---|---|
| 2 | researcher | 4,549 chars, `thought: true` |
| 3 | researcher | same 4,549 chars, final |
| 7 | judge | 513 chars, `thought: true` |
| 8 | judge | same 513 chars, final |
| 13 | content_builder | 5,659 chars, `thought: true` |
| 14 | content_builder | same 5,659 chars, final |

So the result shown to the user was research findings + judge JSON + course, each repeated (`"status": "pass"` appeared twice in it).

Fixed in `app/main.py` (starter and complete): parts with `thought: true` are skipped and the result is the content builder's final text, falling back to the last other text when the content builder never replies, so error events still show. Same prompt afterwards: 5,464 chars, 8 headings, none repeated, no judge JSON.

The content builder sometimes writes doubled heading markers (`## ## Module 1: ...`). That is in the model's output.

### "A2A protocol" alone is read as Hyperledger Aries

With the prompt "Create a short course on how the A2A protocol lets agents talk to each other", both runs wrote about Aries / DIDComm (123 mentions of Aries and 167 of DIDComm in the orchestrator's events; "Agent2Agent", "Agent Card" and "JSON-RPC" zero). The judge passed it.

Naming the protocol fixes it: "Create a short course on how Google's Agent2Agent (A2A) protocol lets AI agents talk to each other" gave 0 Aries, 0 DIDComm, 4 Agent2Agent. Use the full name in demo prompts.

### Cloud Trace export on Cloud Shell needs a quota project

The web app (`app/main.py:30-35`) always installs a `CloudTraceSpanExporter`; the four agents only trace with `--trace_to_cloud`. On Cloud Shell the credentials come from the metadata server, there is no ADC file, so `gcloud auth application-default set-quota-project` fails with "Application default credentials have not been set up". Every export then fails with `403 ... cloudtrace.googleapis.com API requires a quota project`.

Setting the quota project in the environment works:

```
GOOGLE_CLOUD_QUOTA_PROJECT=aisprint-491218 make run
```

After that: 0 export errors in the log, and the request's `POST /api/chat_stream` span (19:19:55–19:20:50 UTC, 54 s) is in Cloud Trace for `aisprint-491218`.

### Machine setup for `make check` and `make run`

- ruff and claat were missing. ruff: `python3 -m pip install --user --break-system-packages ruff` (Ubuntu 24.04 has no apt package), lands in `~/.local/bin`. claat: `go install github.com/googlecodelabs/tools/claat@latest`, lands in `~/go/bin`. Neither directory is on `PATH` by default.
- `lsof` is missing on Cloud Shell, so `run_local.sh` frees ports 8000–8004 with `fuser -k`. Check with `ss -ltnp | grep -E ':800[0-4]'`.
- The `make test` docs diff ignores claat's `"updated"` timestamp and its empty `img/` (commit 5e375cb); both differ per checkout.
- Project `aisprint-491218` also receives `/api/tick` traces about once a minute from another service. Filter on `root:"POST /api/chat_stream"` when looking for this app's spans.

## 2026-11-25: Cloud Run deploy

`make deploy` to `aisprint-491218`, region `us-central1` (no `GOOGLE_CLOUD_LOCATION` or compute region set, so `deploy.sh` defaults to it). All five services deployed with exit 0, no prompts:

| Service | URL | Access |
|---|---|---|
| researcher | https://researcher-289270257791.us-central1.run.app | authenticated only |
| content-builder | https://content-builder-289270257791.us-central1.run.app | authenticated only |
| judge | https://judge-289270257791.us-central1.run.app | authenticated only |
| orchestrator | https://orchestrator-289270257791.us-central1.run.app | authenticated only |
| course-creator (web app) | https://course-creator-289270257791.us-central1.run.app | public |

One request through the public web app with the Agent2Agent prompt: 27 s, 5,477 chars, 8 headings, none repeated, no judge JSON.

Before deploying, all five images were built from dereferenced tars and started with `PORT=8080`: agent cards and `/list-apps` returned 200. The web app's only traceback in the local container was Cloud Trace export without credentials.
