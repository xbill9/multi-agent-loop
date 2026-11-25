summary: Build a team of AI agents with ADK 2.0 and A2A that research a topic, judge the research and write a course, then deploy them to Cloud Run.
id: building-a-multi-agent-system-adk2
categories: AI, Cloud Run, ADK
tags: workshop
status: Published
authors: William McLean
feedback link: https://github.com/xbill9/multi-agent-loop/issues

# Building a Multi-Agent System with ADK 2.0 and A2A

## Overview
Duration: 3

In this codelab you build an **AI course creator**: give it a topic such as "the history of coffee" and it returns a finished course module.

Four agents share the work:

* **Researcher** gathers information on the topic with Google Search.
* **Judge** grades the research and returns `pass` or `fail` with feedback.
* **Content builder** turns approved research into a course with a title and sections.
* **Orchestrator** runs the researcher and judge in a loop until the judge passes (up to three rounds), then hands the research to the content builder.

Each agent is its own service. The orchestrator talks to the other three over the **Agent2Agent (A2A)** protocol, so each one can be deployed, scaled and replaced on its own.

### What you'll learn

* Define agents with the Agent Development Kit (ADK) 2.0
* Return structured output from an agent with a Pydantic schema
* Write a custom agent that ends a loop
* Combine agents with `LoopAgent` and `SequentialAgent`
* Call remote agents over A2A with `RemoteA2aAgent`
* Run the system locally and deploy it to Cloud Run

### What you need

* A Google Cloud project with billing turned on (workshop credits work)
* A browser; everything runs in Cloud Shell

<aside class="positive">
This codelab is an update of Google's <a href="https://codelabs.developers.google.com/codelabs/production-ready-ai-roadshow/1-building-a-multi-agent-system/building-a-multi-agent-system">Building a Multi-Agent System</a> for google-adk 2.15 and a2a-sdk 1.3. The code is in <a href="https://github.com/xbill9/multi-agent-loop">xbill9/multi-agent-loop</a>.
</aside>

## Claim credits and create a project
Duration: 10

### Claim your credits

1. Open the claim link from your workshop organizer and sign in with a **personal Gmail** account.
2. Join the Google Developer Program and claim the badge if asked.
3. Finish the verification on your phone.
4. Wait 2 to 5 minutes for the trial billing account to appear.

<aside class="negative">
<strong>CRED-101</strong> means you are signed in with a work or school account. Switch to your @gmail.com account.<br>
<strong>CRED-103</strong> means verification failed. Refresh and retry, or switch your phone to mobile data.
</aside>

### Create a project

1. Open [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate).
2. Name the project and pick the **trial billing account** from your credit.
3. Click **Create** and copy the **project ID**.

## Set up your environment
Duration: 8

Open [Cloud Shell](https://shell.cloud.google.com) and point it at your project:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud auth list
```

`gcloud auth list` should show your Gmail account as active.

Enable the APIs the lab uses:

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  compute.googleapis.com \
  cloudtrace.googleapis.com \
  logging.googleapis.com
```

The agents send traces to Cloud Trace, so leaving that API off fills the logs with `PERMISSION_DENIED` errors.

Clone the repository and move into the starter:

```bash
git clone https://github.com/xbill9/multi-agent-loop.git
cd multi-agent-loop/codelab-starter
```

Install the dependencies for all four agents and the web app:

```bash
python3 -m pip install -r requirements.txt
```

Cloud Shell installs the packages into `~/.local`, on its Python 3.12. pip then lists conflicts with tools Cloud Shell has preinstalled, such as `google-agents-cli` and `litellm`; the lab uses none of them, so you can ignore those lines. Check the result:

```bash
adk --version
```

It should print `adk, version 2.15.0` or newer.

<aside class="negative">
On your own machine, pip may stop with <code>externally-managed-environment</code>. Add <code>--user</code> to the install command.
</aside>

Create the environment file and load it:

```bash
cp .env.example .env
sed -i "s/^GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=\"$(gcloud config get-value project)\"/" .env
set -a; source .env; set +a
```

The starter has one folder per agent under `agents/`, plus the web app in `app/`. Each agent folder has an `agent.py` with `TODO` comments that you fill in over the next steps.

## Build the researcher
Duration: 5

The researcher is a single ADK `Agent`: a model, a description that other agents read, and an instruction.

Open `agents/researcher/agent.py` and replace the `TODO` with:

```python
# --- Researcher Agent ---
researcher = Agent(
    name="researcher",
    model=MODEL,
    description="Gathers information on a topic using Google Search.",
    instruction="""
    You are an expert researcher. Your goal is to find comprehensive and accurate information on the user's topic.
    Summarize your findings clearly.
    If you receive feedback that your research is insufficient, use the feedback to refine your next search.
    DO NOT output any function calls. Provide your research directly as text.
    """,
)

root_agent = researcher
```

`root_agent` is the name ADK looks for when it loads the folder as an agent.

## Build the judge
Duration: 5

The judge returns structured feedback instead of free text. A Pydantic model defines the shape, and `output_schema` makes the agent answer in that shape.

Open `agents/judge/agent.py` and replace both `TODO`s with:

```python
# --- Data Models ---
class JudgeFeedback(BaseModel):
    """Structured feedback from the Judge agent."""
    status: Literal["pass", "fail"] = Field(
        description="Whether the research is sufficient ('pass') or needs more work ('fail')."
    )
    feedback: str = Field(
        description="Detailed feedback on what is missing or needs clarification if status is 'fail'. If 'pass', a brief confirmation."
    )

# --- Judge Agent ---
judge = Agent(
    name="judge",
    model=MODEL,
    description="Evaluates research findings for completeness and accuracy.",
    instruction="""
    You are a strict editor and fact-checker.
    Evaluate the 'research_findings' against the user's original request.
    Determine if the findings are sufficient to create a high-quality course.
    If they are good enough, output status='pass'.
    If they are missing key information, are too vague, or likely inaccurate, output status='fail' and provide specific, constructive 'feedback' on what to research next.
    """,
    output_schema=JudgeFeedback,
    # Disallow transfers as it uses output_schema
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = judge
```

## Test each agent alone
Duration: 5

`adk run` loads an agent folder and sends it one message, so you can check each agent before wiring them together.

Ask the researcher a question:

```bash
adk run agents/researcher "Find the population of Tokyo in 2020"
```

The researcher answers with figures from the 2020 census.

Give the judge some thin research:

```bash
adk run agents/judge "Topic: Tokyo. Findings: Tokyo is a city."
```

The judge returns JSON with `"status": "fail"` and a list of what is missing:

```json
{"status": "fail", "feedback": "The findings are extremely insufficient for creating a high-quality course. ..."}
```

## Build the content builder
Duration: 3

The content builder writes the course from the approved research. The headings matter: the web app turns the `##` sections into a table of contents.

Open `agents/content_builder/agent.py` and replace the `TODO` with:

```python
# --- Content Builder Agent ---
content_builder = Agent(
    name="content_builder",
    model=MODEL,
    description="Transforms research findings into a structured course.",
    instruction="""
    You are an expert course creator.
    Take the approved 'research_findings' and transform them into a well-structured, engaging course module.

    **Formatting Rules:**
    1. Start with a main title using a single `#` (H1).
    2. Use `##` (H2) for main section headings. These will be used for the Table of Contents.
    3. Use bullet points and clear paragraphs.
    4. Maintain a professional but engaging tone.

    Ensure the content directly addresses the user's original request.
    """,
)

root_agent = content_builder
```

## Connect to the agents over A2A
Duration: 7

The orchestrator runs in its own process and reaches the other three agents over A2A. `RemoteA2aAgent` reads an agent's **agent card**, a JSON file that describes the agent and where to send messages, and then behaves like a local agent.

Each agent serves its card at `/a2a/agent/.well-known/agent-card.json`. The URLs come from environment variables, so the same code runs locally and on Cloud Run.

Open `agents/orchestrator/agent.py` and replace the remote-agents `TODO` with:

```python
# Connect to the Researcher (Localhost port 8001)
researcher_url = os.environ.get(
    "RESEARCHER_AGENT_CARD_URL",
    "http://localhost:8001/.well-known/agent.json"
)
researcher = RemoteA2aAgent(
    name="researcher",
    agent_card=researcher_url,
    description="Gathers information using Google Search.",
    # IMPORTANT: Save the output to state for the Judge to see
    after_agent_callback=create_save_output_callback("research_findings"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(researcher_url)
)

# Connect to the Judge (Localhost port 8002)
judge_url = os.environ.get(
    "JUDGE_AGENT_CARD_URL",
    "http://localhost:8002/.well-known/agent.json"
)
judge = RemoteA2aAgent(
    name="judge",
    agent_card=judge_url,
    description="Evaluates research.",
    after_agent_callback=create_save_output_callback("judge_feedback"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(judge_url)
)

# Content Builder (Localhost port 8003) - Implementation hidden for this lab
content_builder_url = os.environ.get(
    "CONTENT_BUILDER_AGENT_CARD_URL",
    "http://localhost:8003/.well-known/agent.json"
)
content_builder = RemoteA2aAgent(
    name="content_builder",
    agent_card=content_builder_url,
    description="Builds the course.",
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(content_builder_url)
)
```

Two details make the agents work together:

* The `after_agent_callback` saves each agent's answer into session state, under `research_findings` and `judge_feedback`. The judge reads the research from there, and the next step reads the verdict.
* `create_authenticated_client` adds a Google ID token to each request, which Cloud Run needs when the agents only accept authenticated calls.

## End the loop when the judge passes
Duration: 5

A loop needs a way to stop. ADK ends a `LoopAgent` when one of its agents sends an event with `escalate=True`. The escalation checker is a small custom agent that reads the judge's verdict from state and escalates on a pass.

Replace the `EscalationChecker` `TODO` with:

```python
class EscalationChecker(BaseAgent):
    """Checks the judge's feedback and escalates (breaks the loop) if it passed."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        feedback = ctx.session.state.get("judge_feedback")

        # Debug log to see what we got from the remote agent
        print(f"[EscalationChecker] Feedback received: {feedback}")

        if feedback and isinstance(feedback, dict) and feedback.get("status") == "pass":
            yield Event(author=self.name, actions=EventActions(escalate=True))
        elif isinstance(feedback, str) and '"status": "pass"' in feedback:
             yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)

escalation_checker = EscalationChecker(name="escalation_checker")
```

The `str` branch covers a verdict that arrives as text instead of parsed JSON.

## Build the research loop and the pipeline
Duration: 5

Two workflow agents put the pieces in order. They call no model themselves; they decide which agent runs next.

Replace the last two `TODO`s with:

```python
research_loop = LoopAgent(
    name="research_loop",
    description="Iteratively researches and judges until quality standards are met.",
    sub_agents=[researcher, judge, escalation_checker],
    max_iterations=3,
)

root_agent = SequentialAgent(
    name="course_creation_pipeline",
    description="A pipeline that researches a topic and then builds a course from it.",
    sub_agents=[research_loop, content_builder],
)
```

* `LoopAgent` runs researcher, judge and escalation checker in turn, at most three times. On a fail, the researcher sees the judge's feedback and searches again.
* `SequentialAgent` runs the loop, then the content builder.

## Run everything locally
Duration: 10

`run_local.sh` starts the three agents on ports 8001 to 8003, the orchestrator on 8004 and the web app on 8000:

```bash
./run_local.sh
```

Check that each agent serves its card. In a second Cloud Shell tab:

```bash
for p in 8001 8002 8003; do
  curl -s http://localhost:$p/a2a/agent/.well-known/agent-card.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['name'], d['supportedInterfaces'][0]['url'])"
done
```

Each line shows an agent name and its A2A address, such as `researcher http://localhost:8001/a2a/agent`.

Open the app: in Cloud Shell click **Web Preview**, then **Change port**, enter `8000` and click **Change and Preview**. Enter:

```
Create a course about the history of coffee.
```

The page shows the researcher, then the judge, then the content builder at work, and ends with the finished course.

<aside class="negative">
If an agent reports missing credentials, run <code>gcloud auth application-default login</code> and start <code>./run_local.sh</code> again.
</aside>

Stop everything with **Ctrl+C** in the first tab.

## Deploy to Cloud Run
Duration: 15

`deploy.sh` deploys five Cloud Run services from source: `researcher`, `judge`, `content-builder`, `orchestrator` and the `course-creator` web app. The four agent services only accept authenticated calls; the web app is public.

```bash
./deploy.sh
```

On a new project, the first deploy asks to create an Artifact Registry repository for the container images. Answer `Y`. The five builds take about 15 minutes in total.

The script reads each agent's URL after it deploys and passes the agent card addresses to the orchestrator:

```bash
--set-env-vars RESEARCHER_AGENT_CARD_URL=$RESEARCHER_URL/a2a/agent/.well-known/agent-card.json
```

When it finishes, open the `course-creator` URL and try another topic.

<aside class="positive">
The region comes from <code>gcloud config get-value compute/region</code>, and the script falls back to <code>us-central1</code> when it is unset.
</aside>

## Clean up and next steps
Duration: 2

Delete the services so they stop using your credits:

```bash
for s in course-creator orchestrator researcher judge content-builder; do
  gcloud run services delete $s --region us-central1 --quiet
done
```

Use the region you deployed to if it differs.

### Where to go next

* Compare your code with the finished version in `codelab-complete/`.
* Give each agent its own model, such as a faster model for the judge.
* Add tools to the researcher beyond Google Search.
* See [xbill9/multi-agent](https://github.com/xbill9/multi-agent) for the same four agents with a streaming web app, guard and progress agents, and GKE deployment.

### What changed for ADK 2.0

* Dependencies are google-adk 2.15 and a2a-sdk 1.3, installed with pip on the current Python.
* ADK 2.0 would serve an agent's A2A routes under its folder name. `shared/adk_app.py` mounts them at `/a2a/agent`, so the card addresses stay the same locally and on Cloud Run.
* a2a-sdk 1.x agent cards list addresses under `supportedInterfaces` instead of a single `url`, and `shared/a2a_utils.py` rewrites both forms.
* `adk run` takes a message as an argument, so you can test an agent in one command.
