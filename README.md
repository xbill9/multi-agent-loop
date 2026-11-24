# Building a Multi-Agent System: workshop demo

Demo code and slides for the hands-on session at Pace University (New York), Wednesday, December 2, 2026.

**Codelab: https://xbill9.github.io/multi-agent-loop/building-a-multi-agent-system-adk2/**

It updates Google's codelab [Building a Multi-Agent System](https://codelabs.developers.google.com/codelabs/production-ready-ai-roadshow/1-building-a-multi-agent-system/building-a-multi-agent-system) from the Production-Ready AI Roadshow for google-adk 2.15 and a2a-sdk 1.3.

## Codelab

[Building a Multi-Agent System with ADK 2.0 and A2A](https://xbill9.github.io/multi-agent-loop/building-a-multi-agent-system-adk2/): the step-by-step lab for this repo, updated for google-adk 2.15 and a2a-sdk 1.3. Source: `codelab/building-a-multi-agent-system-adk2.md`; rebuild with `claat export -o docs codelab/building-a-multi-agent-system-adk2.md`.

## What's here

| Folder | Contents |
|---|---|
| `codelab-starter/` | The starter attendees clone, with `TODO`s for each agent |
| `codelab-complete/` | The finished solution: researcher, judge, content builder, orchestrator and web app |

Both come from [GoogleCloudPlatform/devrel-demos](https://github.com/GoogleCloudPlatform/devrel-demos/tree/main/agents/build-with-ai/production-ready-ai) under the Apache 2.0 license (see `LICENSE`), updated to run on the latest Python, google-adk 2.x and a2a-sdk 1.x.

## The system

- **Researcher:** an ADK agent that gathers information with Google Search
- **Judge:** returns `pass` or `fail` with feedback as a Pydantic schema
- **Escalation checker:** a custom `BaseAgent` that ends the loop when the judge passes
- **Research loop:** `LoopAgent` over researcher, judge and checker, up to 3 rounds
- **Pipeline:** `SequentialAgent` runs the loop, then the content builder
- **Orchestrator:** calls each agent over A2A; every agent is its own Cloud Run service

## Run it

You need a Google Cloud project with billing on (workshop credits work).

```bash
cd codelab-complete
cp .env.example .env    # set GOOGLE_CLOUD_PROJECT
source .env
python3 -m pip install -r requirements.txt
./run_local.sh          # agents on 8001-8004, web app on 8000
```

Open http://localhost:8000 (in Cloud Shell, Web Preview on port 8000) and try "Create a course about the history of coffee."

Deploy to Cloud Run with `./deploy.sh`, or follow step 12 of the codelab.

## Slides

[Building a Multi-Agent System - Pace GDG 2026-12-02](https://docs.google.com/presentation/d/1FVo8PcPUvdesq0asK6dQBcKdsSF0TGisCLlpe0v6C_w/view)

## Going further

[xbill9/multi-agent](https://github.com/xbill9/multi-agent) extends the same four agents with a streaming web app, guard and progress agents, GKE deployment and MCP.
