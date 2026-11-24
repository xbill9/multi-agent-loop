# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import os
import logging
import sys
import typing
import warnings

import click
import uvicorn

from google.adk.cli import fast_api
from google.adk.cli.utils import logs


warnings.filterwarnings(
    "ignore",
    message=r".*\[EXPERIMENTAL\].*",
    category=UserWarning
)
os.environ["ADK_SUPPRESS_EXPERIMENTAL_FEATURE_WARNINGS"] = "True"

sys.path.insert(0, os.path.dirname(__file__))

LOG_LEVELS = click.Choice(
    ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    case_sensitive=False,
)

A2A_PREFIX = "/a2a/agent"


def _mount_a2a(app: typing.Any, agents_dir: str) -> None:
    """Serves the agent over A2A at /a2a/agent, whatever its folder is called.

    ADK 2 runs a folder that contains agent.py in single-agent mode and would
    mount A2A under the folder name (/a2a/researcher locally, /a2a/app in the
    container). The orchestrator and the codelab expect /a2a/agent, so the
    routes are mounted here instead of through get_fast_api_app(a2a=True).
    """
    import importlib

    from a2a.server.tasks import (
        InMemoryPushNotificationConfigStore,
        InMemoryTaskStore,
    )
    from a2a.types import AgentCapabilities
    from google.adk.a2a import _compat
    from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
    from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
    from google.adk.apps import App
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.memory import InMemoryMemoryService
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

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


@click.command()
@click.argument(
    "agents_dir",
    type=click.Path(
        exists=True, dir_okay=True, file_okay=False, resolve_path=True
    ),
    default=os.getcwd(),
)
@click.option(
    "--host",
    type=str,
    help="Optional. The binding host of the server",
    default="127.0.0.1",
    show_default=True,
)
@click.option(
    "--port",
    type=int,
    help="Optional. The port of the server",
    default=os.getenv("PORT", 8000),
    show_default=True
)
@click.option(
    "--allow_origins",
    help="Optional. Any additional origins to allow for CORS.",
    multiple=True,
)
@click.option(
    "--eval_storage_uri",
    type=str,
    help=(
        "Optional. The evals storage URI to store agent evals,"
        " supported URIs: gs://<bucket name>."
    ),
    default=None,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    show_default=True,
    default=False,
    help="Enable verbose (DEBUG) logging. Shortcut for --log_level DEBUG.",
)
@click.option(
    "--log_level",
    type=LOG_LEVELS,
    default="INFO",
    help="Optional. Set the logging level",
)
@click.option(
    "--trace_to_cloud",
    is_flag=True,
    show_default=True,
    default=False,
    help="Optional. Whether to enable cloud trace for telemetry.",
)
@click.option(
    "--otel_to_cloud",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Optional. Whether to write OTel data to Google Cloud"
        " Observability services - Cloud Trace and Cloud Logging."
    ),
)
@click.option(
    "--session_service_uri",
    help=(
        """Optional. The URI of the session service.
      - Use 'agentengine://<agent_engine>' to connect to Agent Engine
        sessions. <agent_engine> can either be the full qualified resource
        name 'projects/abc/locations/us-central1/reasoningEngines/123' or
        the resource id '123'.
      - Use 'sqlite://<path_to_sqlite_file>' to connect to an aio-sqlite
        based session service, which is good for local development.
      - Use 'postgresql://<user>:<password>@<host>:<port>/<database_name>'
        to connect to a PostgreSQL DB.
      - See https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls
        for more details on other database URIs supported by SQLAlchemy."""
    ),
)
@click.option(
    "--artifact_service_uri",
    type=str,
    help=(
        "Optional. The URI of the artifact service,"
        " supported URIs: gs://<bucket name> for GCS artifact service."
    ),
    default=None,
)
@click.option(
    "--memory_service_uri",
    type=str,
    help=("""Optional. The URI of the memory service."""),
    default=None,
)
@click.option(
    "--with_web_ui",
    is_flag=True,
    show_default=True,
    default=False,
    help="Optional. Whether to enable ADK Web UI.",
)
@click.option(
    "--url_prefix",
    type=str,
    default=None,
    help="Optional. The URL prefix for the ADK API server.",
)
@click.option(
    "--extra_plugins",
    multiple=True,
    default=None,
    help="Optional. Extra plugins to load.",
)
@click.option(
    "--a2a",
    is_flag=True,
    show_default=True,
    default=False,
    help="Optional. Whether to enable A2A endpoint.",
)
def main(
    agents_dir: str,
    host: str,
    port: int,
    allow_origins: typing.Optional[typing.List[str]],
    eval_storage_uri: typing.Optional[str] = None,
    verbose: bool = False,
    log_level: str = "INFO",
    trace_to_cloud: bool = False,
    otel_to_cloud: bool = False,
    session_service_uri: typing.Optional[str] = None,
    artifact_service_uri: typing.Optional[str] = None,
    memory_service_uri: typing.Optional[str] = None,
    with_web_ui: typing.Optional[bool] = None,
    url_prefix: typing.Optional[str] = None,
    extra_plugins: typing.Optional[typing.List[str]] = None,
    a2a: bool = False
):
    """Starts a FastAPI server for agents.

    AGENTS_DIR: The directory of agents, where each sub-directory is a single
    agent.
    """
    if verbose:
        log_level = "DEBUG"

    logs.setup_adk_logger(getattr(logging, log_level.upper()))

    reload = False
    reload_agents = False

    app = fast_api.get_fast_api_app(
        agents_dir=agents_dir,
        session_service_uri=session_service_uri,
        artifact_service_uri=artifact_service_uri,
        memory_service_uri=memory_service_uri,
        eval_storage_uri=eval_storage_uri,
        allow_origins=allow_origins,
        web=with_web_ui or False,
        trace_to_cloud=trace_to_cloud,
        otel_to_cloud=otel_to_cloud,
        host=host,
        port=port,
        url_prefix=url_prefix,
        reload_agents=reload_agents,
        extra_plugins=extra_plugins,
    )
    if a2a:
        _mount_a2a(app, agents_dir)
        from a2a_utils import a2a_card_dispatch
        from starlette.middleware.base import BaseHTTPMiddleware
        app.add_middleware(BaseHTTPMiddleware, dispatch=a2a_card_dispatch)
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level.lower(),
    )
    server = uvicorn.Server(config)
    server.run()


################################################################################
if __name__ == "__main__":
    main()
