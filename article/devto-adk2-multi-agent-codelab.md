---
title: "Updating Google's Multi-Agent Codelab for ADK 2.0 and A2A 1.x"
published: false
description: "The Production-Ready AI Roadshow codelab, a researcher, judge, content builder and orchestrator talking over A2A, moved to google-adk 2.15 and a2a-sdk 1.3 and tested from Cloud Shell through Cloud Run."
tags: adk, a2a, googlecloud, python
cover_image: https://raw.githubusercontent.com/xbill9/multi-agent-loop/main/article/devto-cover.3fecde3f.jpg
---

This article provides a step by step guide to updating Google's "Building a Multi-Agent System" codelab for ADK 2.0 and later. Four agents research a topic, judge the research and write a course, and the orchestrator reaches the other three over A2A. The update moves them to google-adk 2.15 and a2a-sdk 1.3, runs them on the latest Python, and deploys them to Cloud Run.

https://github.com/xbill9/multi-agent-loop

**The agent code moved to ADK 2.0 unchanged; every change sits in the code that serves the agents over A2A, and in packaging.** ADK 2.0 mounts an agent's A2A routes under its folder name, a2a-sdk 1.x sends agent cards in a new shape and needs an extra package to serve them, and current fastapi needs Python 3.11. With those handled, the whole codelab ran end to end in Cloud Shell, locally and on Cloud Run.

The updated codelab: https://xbill9.github.io/multi-agent-loop/building-a-multi-agent-system-adk2/

---

#### What Was Built?

| Agent | Built with | Role | Local port |
| :--- | :--- | :--- | :--- |
| Researcher | ADK `Agent` | Gathers information on the topic with Google Search | 8001 |
| Judge | ADK `Agent` with `output_schema` | Returns `pass` or `fail` and feedback as a Pydantic model | 8002 |
| Content builder | ADK `Agent` | Writes the course module from approved research | 8003 |
| Orchestrator | `SequentialAgent`, `LoopAgent`, `RemoteA2aAgent` | Loops researcher and judge up to three times, then calls the content builder | 8004 |
| Course creator | FastAPI web app | Streams the orchestrator's progress and shows the course | 8000 |

Each agent is its own service. The orchestrator reads each remote agent's card from `/a2a/agent/.well-known/agent-card.json` and sends it messages over A2A. A custom `BaseAgent`, the escalation checker, ends the loop when the judge passes.

The repository holds two copies of the code: `codelab-starter/`, where the agent files carry `TODO` comments for attendees, and `codelab-complete/`, the finished version.

---

#### At This Point You Should Have…

- A Google Cloud project with billing on (workshop credits work)
- Cloud Shell, or a machine with Python 3.11 or newer and the gcloud CLI
- The Vertex AI, Cloud Run, Cloud Build, Artifact Registry, Compute, Cloud Trace and Cloud Logging APIs enabled

---

#### Step 1 — Install With pip on the Latest Python

One `requirements.txt` covers all four agents and the web app:

```bash
cd multi-agent-loop/codelab-starter
python3 -m pip install -r requirements.txt
adk --version
```

```
adk, version 2.15.0
```

The pins are lower bounds at the newest releases, with no upper caps:

```
a2a-sdk[http-server]>=1.3.1
fastapi>=0.165.0
google-adk>=2.15.0
google-cloud-logging>=3.17.1
google-genai>=2.34.0
httpx>=0.28.1
httpx_sse>=0.4.3
opentelemetry-exporter-gcp-trace>=1.15.0
uvicorn>=0.54.0
```

google-adk 2.15.0 declares `google-genai>=2.34,<3`, so `google-genai>=2.34.0` lets pip pick the newest release ADK accepts.

In Cloud Shell, which runs Python 3.12.3, pip installs into `~/.local` because Cloud Shell's pip configuration sets `break-system-packages`. pip then lists conflicts with tools Cloud Shell has preinstalled; the codelab uses none of them. The same install runs on the workstation's Python 3.14.7.

---

#### Step 2 — Keep A2A at `/a2a/agent`

ADK 2.0 treats a folder that contains `agent.py` as a single agent and takes the agent's name from the folder:

```
242:  is_single_agent = is_single_agent_directory(agents_path)
247:    single_agent_name = agents_path.name
248:    agents_dir = str(agents_path.parent)
503:              prefix=f"/a2a/{app_name}",
```

Each agent starts from its own folder with `adk_app.py ... --a2a .`, so with `get_fast_api_app(a2a=True)` the researcher's card moves to `/a2a/researcher/.well-known/agent-card.json` and `/a2a/agent/...` answers 404. The orchestrator, the deploy script and the codelab all address `/a2a/agent`.

`shared/adk_app.py` now builds the agent card and mounts the A2A routes itself, at a fixed prefix:

```python
A2A_PREFIX = "/a2a/agent"

def _mount_a2a(app: typing.Any, agents_dir: str) -> None:
    sys.path.insert(0, os.path.abspath(agents_dir))
    agent = importlib.import_module("agent").root_agent
    if isinstance(agent, App):
        agent = agent.root_agent

    card = asyncio.run(AgentCardBuilder(
        agent=agent,
        rpc_url=f"http://127.0.0.1{A2A_PREFIX}",
        capabilities=AgentCapabilities(streaming=True),
    ).build())
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
        memory_service=InMemoryMemoryService(),
    )
    _compat.attach_a2a_routes_to_app(
        app,
        agent_card=card,
        agent_executor=A2aAgentExecutor(runner=runner),
        task_store=InMemoryTaskStore(),
        push_config_store=InMemoryPushNotificationConfigStore(),
        prefix=A2A_PREFIX,
    )
```

`get_fast_api_app` is called without `a2a=True`, and `_mount_a2a(app, agents_dir)` runs right after it. The cards are back at the same path for every agent:

```
8001 researcher ['http://localhost:8001/a2a/agent']
8002 judge ['http://localhost:8002/a2a/agent']
8003 content_builder ['http://localhost:8003/a2a/agent']
```

---

#### Step 3 — Agent Cards in the a2a-sdk 1.x Shape

a2a-sdk 1.x builds agent cards as protobuf messages, so the card has no `model_dump_json()`. ADK's own helper writes either version to a dict:

```python
card_json = json.dumps(_compat.a2a_to_dict(agent_card), indent=2)
```

The card lists its endpoints under `supportedInterfaces`:

```json
{"name": "researcher", "supportedInterfaces": [{"url": "http://127.0.0.1/a2a/researcher", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}], "capabilities": {"streaming": true}}
```

The codelab's middleware rewrites the card's address to the host the request came in on, which is what lets one card work on localhost and behind Cloud Run. It now rewrites both shapes:

```python
# a2a-sdk 0.3.x keeps the endpoint in "url";
# 1.x keeps one per entry in "supportedInterfaces".
if "url" in card:
    card["url"] = rewrite(card["url"])
for iface in card.get("supportedInterfaces", []):
    if "url" in iface:
        iface["url"] = rewrite(iface["url"])
```

`a2a.utils.constants` in 1.3.1 defines only `AGENT_CARD_WELL_KNOWN_PATH`, so the two older card paths the middleware also matches, `/.well-known/agent.json` and `/agent/authenticatedExtendedCard`, are local constants.

---

#### Step 4 — Test One Agent With `adk run`

In ADK 2.0, `adk run` takes the message as an argument:

```
Usage: adk run [OPTIONS] AGENT [QUERY]
```

So each agent can be checked in one command before the system is wired together:

```bash
adk run agents/judge "Topic: Tokyo. Findings: Tokyo is a city."
```

```
[judge]: {"status":"fail","feedback":"The finding 'Tokyo is a city' is far too brief and lacks the depth necessary to create a high-quality course. ...
```

```bash
adk run agents/researcher "Find the population of Tokyo in 2020"
```

```
[researcher]: The population of Tokyo in 2020 was approximately **14,047,594** people.
```

---

#### Step 5 — Run All Five Services Locally

`run_local.sh` starts the agents with `python3` and the web app with `python3 -m uvicorn`:

```bash
./run_local.sh
```

In Cloud Shell all five ports were listening 9 seconds after start. One prompt to the web app's stream endpoint:

```bash
curl -sN -X POST http://localhost:8000/api/chat_stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a short course about the history of coffee", "user_id": "cs"}'
```

```
Counter({'progress': 24, 'result': 1})
chars 36020 h2 42
```

24 progress events, then one course of 36,020 characters with 42 `##` sections.

---

#### Step 6 — `requires-python = ">=3.11"` for the Container Build

The agents run locally with pip, and the Dockerfiles install with `uv sync`. uv resolves for every Python version `requires-python` allows, so `>=3.10` fails against fastapi 0.165 in Cloud Build even though the container runs Python 3.12:

```
error: No solution found when resolving dependencies for split (markers: python_full_version == '3.10.*')
  cause: Because the requested Python version (>=3.10) does not satisfy Python>=3.11 and fastapi==0.165.0 depends on Python>=3.11, we can conclude that fastapi==0.165.0 cannot be used.
```

Every `pyproject.toml` now has `requires-python = ">=3.11"`, with no upper bound, and `uv lock` in each agent folder refreshes the lock files. `uv lock` only resolves and creates no virtual environment.

---

#### Step 7 — `a2a-sdk[http-server]` for the A2A Routes

a2a-sdk 1.x imports `sse-starlette` when the A2A server routes load, and ships it only in extras:

```
sse-starlette; extra == 'all'
sse-starlette; extra == 'fastapi'
sse-starlette; extra == 'http-server'
```

A container built from plain `a2a-sdk` stops at startup:

```
  File "/opt/venv/lib/python3.12/site-packages/a2a/compat/v0_3/jsonrpc_adapter.py", line 6, in <module>
ModuleNotFoundError: No module named 'sse_starlette'
```

The agents now depend on `a2a-sdk[http-server]>=1.3.1`. A workstation that already has `sse-starlette` installed for another project runs the agents either way, which is why the container is the place to check.

---

#### Step 8 — Deploy to Cloud Run

`deploy.sh` deploys five services from source. The four agent services accept only authenticated calls, and the orchestrator reaches them with Google ID tokens; the web app is public:

```bash
./deploy.sh
```

```
Service URL: https://researcher-1056842563084.us-central1.run.app
Service URL: https://content-builder-1056842563084.us-central1.run.app
Service URL: https://judge-1056842563084.us-central1.run.app
Service URL: https://orchestrator-1056842563084.us-central1.run.app
Service URL: https://course-creator-1056842563084.us-central1.run.app
DEPLOY_EXIT=0
```

One prompt to the deployed web app, then each agent card fetched with no credentials:

```
home: 200
Counter({'progress': 14, 'result': 1})
chars 25470 h2 12
researcher unauth: 403
judge unauth: 403
content-builder unauth: 403
orchestrator unauth: 403
```

The codelab's last step deletes the five services:

```bash
for s in course-creator orchestrator researcher judge content-builder; do
  gcloud run services delete $s --region us-central1 --quiet
done
```

---

#### Step 9 — Publish the Codelab With claat

The codelab text is one markdown file in claat format, `codelab/building-a-multi-agent-system-adk2.md`, exported to static HTML and served by GitHub Pages:

```bash
claat export -o docs codelab/building-a-multi-agent-system-adk2.md
```

The `googlecodelabs/tools` repository that holds claat is archived; `go install github.com/googlecodelabs/tools/claat@latest` still builds it, and the exported page loads its styles and scripts from `storage.googleapis.com/claat-public`.

---

#### 🔎 Tip: Build and Start One Agent Image Before Deploying

A shared workstation Python can satisfy an import that the container cannot. Building one agent image with `docker build` and starting it with the same command Cloud Run uses shows a missing package in a minute, where a source deploy shows it after a Cloud Build run and a failed revision.

---

#### 🔎 Tip: Give Attendees One `requirements.txt`

Each agent keeps its own `pyproject.toml` for its container. Attendees in Cloud Shell need all of them at once, and one file that merges them installs in a single command.

---

#### 🔎 Tip: Point `adk run` at a Folder With a Message

`adk run agents/judge "..."` returns one answer and exits, which makes each agent testable from a script or a codelab step with its expected output printed underneath.

---

#### Compare and Contrast

| | Original codelab | ADK 2.0 update |
| :--- | :--- | :--- |
| Packages | google-adk 1.x, a2a-sdk 0.3 | google-adk 2.15, a2a-sdk 1.3 with `[http-server]` |
| Python | `>=3.10,<3.14` | `>=3.11`, no upper cap |
| Local install | `uv sync`, `uv run` | `pip install -r requirements.txt` |
| A2A path | `/a2a/agent` from a card file | `/a2a/agent` mounted by `_mount_a2a` |
| Card endpoint field | `url` | `supportedInterfaces[].url` |
| Test one agent | interactive `adk run` | `adk run AGENT "message"` |
| Agent code | four `agent.py` files | the same four files |

---

#### So, Which One?

Workshops scheduled from now on should use the ADK 2.0 version, because a fresh `pip install google-adk` installs ADK 2.x. The original codelab stays correct for anyone pinned to google-adk 1.x and a2a-sdk 0.3.

---

#### Summary

The goal of this article was to move Google's multi-agent codelab to ADK 2.0 and A2A 1.x and keep it runnable from Cloud Shell. The key to the solution was serving each agent over A2A at a fixed `/a2a/agent` path, in the a2a-sdk 1.x card shape, with packaging that matches what the containers install. The results were:

- 🟢 The four agents' `agent.py` files run on google-adk 2.15 unchanged
- 🟢 Agent cards serve at `/a2a/agent` on every agent, locally and on Cloud Run
- 🟢 Cloud Shell runs the whole codelab: install, `adk run` checks, five local services and a 36,020-character course
- 🟢 Five Cloud Run services deployed; the web app returned a course and the four agents answered 403 to unauthenticated requests
- ⚠️ Cloud Shell's pip lists conflicts with its own preinstalled tools after the install
- ⚠️ claat comes from an archived repository
- ❌ `requires-python = ">=3.10"` and plain `a2a-sdk` both fail on Cloud Run, the first in Cloud Build and the second at container start

The checks ran on one Google Cloud project in `us-central1`, from one Cloud Shell VM (Python 3.12.3) and one workstation (Python 3.14.7), one end to end run each, with `gemini-3-flash-preview` on Vertex AI. The credit claim and new-project steps of the codelab were not run.

The strategy for updating a multi-agent A2A codelab to ADK 2.0 was validated with an incremental step by step approach.

---

#### References

- Updated codelab: https://xbill9.github.io/multi-agent-loop/building-a-multi-agent-system-adk2/
- Repository: https://github.com/xbill9/multi-agent-loop
- Original codelab: https://codelabs.developers.google.com/codelabs/production-ready-ai-roadshow/1-building-a-multi-agent-system/building-a-multi-agent-system
- Original code: https://github.com/GoogleCloudPlatform/devrel-demos/tree/main/agents/build-with-ai/production-ready-ai
- Agent Development Kit: https://github.com/google/adk-python
- A2A Python SDK: https://github.com/a2aproject/a2a-python
- claat: https://github.com/googlecodelabs/tools
