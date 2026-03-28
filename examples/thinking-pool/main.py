"""
Advanced Thinking Pool: multi-agent collaborative reasoning with parallel subtasks,
coordination protocols, and interactive observability.

Run from repo root (with PYTHONPATH=. or after pip install -e .):
    PYTHONPATH=. python examples/thinking-pool/main.py

Commands: submit <prompt> | status <task_id> | watch <task_id> | agents | events <task_id> | exit
"""

import asyncio
import contextlib
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Allow running as script: python examples/thinking-pool/main.py (repo root in PYTHONPATH)
_example_dir = Path(__file__).resolve().parent
_repo_root = _example_dir.parents[2]  # .../examples/thinking-pool -> examples -> repo root
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
if str(_example_dir) not in sys.path:
    sys.path.insert(0, str(_example_dir))

from events import format_task_status, get_tracker, list_tracked_root_ids  # noqa: E402
from orchestration import (  # noqa: E402
    DEFAULT_CLAIM_TTL_SEC,
    DEFAULT_REQUEST_TIMEOUT_SEC,
    get_request_status,
    submit_request,
)
from roles import default_role_configs  # noqa: E402

from converge.coordination.bidding import BiddingProtocol  # noqa: E402
from converge.coordination.delegation import DelegationProtocol  # noqa: E402
from converge.coordination.negotiation import NegotiationProtocol  # noqa: E402
from converge.coordination.pool_manager import PoolManager  # noqa: E402
from converge.coordination.task_manager import TaskManager  # noqa: E402
from converge.core.identity import Identity  # noqa: E402
from converge.core.topic import Topic  # noqa: E402
from converge.extensions.llm.agent import LLMAgent  # noqa: E402
from converge.extensions.storage.memory import MemoryStore  # noqa: E402
from converge.network.transport.local import LocalTransport  # noqa: E402
from converge.observability.metrics import MetricsCollector  # noqa: E402
from converge.observability.replay import ReplayLog  # noqa: E402
from converge.policy.admission import OpenAdmission  # noqa: E402
from converge.policy.safety import ActionPolicy  # noqa: E402
from converge.runtime.loop import AgentRuntime  # noqa: E402

try:
    from diagnostics import check_provider_availability, format_boot_banner, format_diagnostics, get_boot_summary
except ImportError:
    def check_provider_availability() -> dict[str, bool]:
        return {}

    def get_boot_summary(
        provider_available: dict[str, bool],
        agents_started: int,
        agents_expected: int,
        pool_id: str,
        *,
        protocols_wired: bool = True,
    ) -> dict[str, Any]:
        return {
            "providers": provider_available,
            "agents_started": agents_started,
            "agents_expected": agents_expected,
            "pool_id": pool_id,
            "protocols_wired": protocols_wired,
            "degraded": True,
        }

    def format_boot_banner(summary: dict[str, Any]) -> list[str]:
        return [f"Pool: {summary.get('pool_id', '?')}"]

    def format_diagnostics(
        summary: dict[str, Any],
        runtimes: list[Any] | None = None,
        task_manager: Any | None = None,
    ) -> list[str]:
        del runtimes, task_manager
        return [f"Pool: {summary.get('pool_id', '?')}"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("thinking_pool")

# Claim TTL and task poll intervals for runtime (reliability and responsiveness)
CLAIM_TTL_INTERVAL_SEC = 30.0
TASK_POLL_INTERVAL_SEC = 2.0


def get_llm_provider(model_config: dict) -> Any:
    """Instantiate the correct LLM provider based on configuration."""
    provider_type = model_config.get("provider", "openai").lower()
    if provider_type == "openai":
        from converge.extensions.llm.openai import OpenAIProvider
        return OpenAIProvider(model=model_config.get("model", "gpt-4o-mini"))
    if provider_type == "anthropic":
        from converge.extensions.llm.anthropic import AnthropicProvider
        return AnthropicProvider(model=model_config.get("model", "claude-3-5-sonnet-latest"))
    if provider_type == "mistral":
        from converge.extensions.llm.mistral import MistralProvider
        return MistralProvider(model=model_config.get("model", "mistral-small-latest"))
    raise ValueError(f"Unknown provider type: {provider_type}")


def _validate_provider_api(provider: str, model: str) -> None:
    """
    Run one minimal chat request to validate the selected provider's API key.
    On 401 Unauthorized (or other auth errors), print a clear message and exit.
    """
    env_var = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "mistral": "MISTRAL_API_KEY"}.get(
        provider, "API_KEY",
    )
    try:
        p = get_llm_provider({"provider": provider, "model": model})
        p.chat([{"role": "user", "content": "Hi"}])
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str:
            print(f"\n  API returned 401 Unauthorized. Check that {env_var} is set and valid.")
            print(f"  Provider: {provider}. Update your key or set a different provider's key and restart.\n")
            raise SystemExit(1) from e
        raise


def _load_env() -> None:
    """Load .env from example or cwd."""
    env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path.cwd() / ".env",
    ]
    try:
        from dotenv import load_dotenv
        for p in env_paths:
            if p.exists():
                load_dotenv(p)
                return
    except ImportError:
        pass
    for p in env_paths:
        if p.exists():
            with p.open() as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'").strip('"')
                    if k not in os.environ:
                        os.environ[k] = v
            return


async def create_pool_agent(
    role_config: dict[str, Any],
    pool_id: str,
    task_manager: TaskManager,
    pool_manager: PoolManager,
    executor_kwargs: dict[str, Any],
    metrics_collector: MetricsCollector | None,
    replay_log: ReplayLog | None,
) -> tuple[LLMAgent, AgentRuntime]:
    """Create one LLM agent with the given role config and join the pool."""
    name = role_config["name"]
    provider_config = {k: role_config.get(k) for k in ("provider", "model")}
    provider_config.setdefault("provider", "openai")
    provider_config.setdefault("model", "gpt-4o-mini")

    identity = Identity.generate()
    provider = get_llm_provider(provider_config)
    prompt = role_config.get("prompt", "")
    full_prompt = (
        f"You are '{name}', participating in a collaborative thinking pool.\n"
        f"Role Instructions: {prompt}\n\n"
        "Use ClaimTask for tasks you can handle, ReportTask with the result when done. "
        "Use SubmitTask only to create new subtasks. You may SendMessage to collaborate. "
        "Output ONLY a valid JSON array of decisions. If you have no decisions, output []."
    )
    agent = LLMAgent(identity=identity, provider=provider, system_prompt=full_prompt)
    agent.capabilities = list(role_config.get("capabilities", []))
    topic_ns = role_config.get("topic_namespace")
    agent.topics = [Topic(namespace=topic_ns, attributes={})] if topic_ns else []

    transport = LocalTransport(agent.id)
    runtime = AgentRuntime(
        agent=agent,
        transport=transport,
        task_manager=task_manager,
        pool_manager=pool_manager,
        executor_kwargs=executor_kwargs,
        metrics_collector=metrics_collector,
        replay_log=replay_log,
        discovery_service=None,  # optional: pass to register agents for discovery
        claim_ttl_interval_sec=CLAIM_TTL_INTERVAL_SEC,
        task_poll_interval_sec=TASK_POLL_INTERVAL_SEC,
    )
    await runtime.start()
    pool_manager.join_pool(agent.id, pool_id)
    return agent, runtime


async def main() -> None:
    _load_env()

    store = MemoryStore()
    pool_manager = PoolManager(store=store)
    task_manager = TaskManager(store=store)
    metrics_collector = MetricsCollector()
    replay_log = ReplayLog()

    # Coordination protocols (shared across runtimes)
    negotiation_protocol = NegotiationProtocol()
    delegation_protocol = DelegationProtocol()
    bidding_protocols = {"main_auction": BiddingProtocol()}
    votes_store: dict[str, list[tuple[str, Any]]] = {}

    action_policy = ActionPolicy(
        allowed_actions=[
            "SubmitTask", "ClaimTask", "ReportTask", "SendMessage", "JoinPool",
            "Propose", "AcceptProposal", "RejectProposal", "Delegate", "RevokeDelegation",
            "Vote", "SubmitBid",
        ],
    )
    executor_kwargs: dict[str, Any] = {
        "safety_policy": (None, action_policy),
        "negotiation_protocol": negotiation_protocol,
        "delegation_protocol": delegation_protocol,
        "bidding_protocols": bidding_protocols,
        "votes_store": votes_store,
        # Do not pass replay_log here: AgentRuntime passes it explicitly to StandardExecutor.
    }

    pool = pool_manager.create_pool({
        "topics": [],
        "admission_policy": OpenAdmission(),
    })
    pool_id = pool.id
    logger.info("Created thinking pool: %s", pool_id)

    # Build role configs using first available provider
    provider = "openai"
    model = os.getenv("POOL_MODEL", "gpt-4o-mini")
    if os.getenv("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        model = os.getenv("POOL_MODEL", "claude-3-5-haiku-20241022")
    elif os.getenv("MISTRAL_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        provider = "mistral"
        model = os.getenv("POOL_MODEL", "mistral-small-latest")

    _validate_provider_api(provider, model)

    role_configs = default_role_configs(provider=provider, model=model)
    runtimes: list[AgentRuntime] = []
    agent_id_to_role: dict[str, str] = {}
    for config in role_configs:
        try:
            agent, runtime = await create_pool_agent(
                config,
                pool_id,
                task_manager,
                pool_manager,
                executor_kwargs,
                metrics_collector,
                replay_log,
            )
            runtimes.append(runtime)
            agent_id_to_role[agent.id] = config["name"]
            logger.info("Started agent: %s", config["name"])
        except ImportError as e:
            logger.warning("Skip agent %s: %s", config["name"], e)
        except Exception as e:
            logger.warning("Skip agent %s: %s", config["name"], e)

    if not runtimes:
        logger.error("No agents started. Check API keys and install [llm] extras.")
        return

    # Boot-time diagnostics summary
    provider_available = check_provider_availability()
    boot_summary = get_boot_summary(
        provider_available=provider_available,
        agents_started=len(runtimes),
        agents_expected=len(role_configs),
        pool_id=pool_id,
        protocols_wired=True,
    )
    for line in format_boot_banner(boot_summary):
        print(line)

    from cli_controller import run_controller
    await run_controller(
        task_manager=task_manager,
        pool_id=pool_id,
        pool_manager=pool_manager,
        replay_log=replay_log,
        submit_request_fn=submit_request,
        get_request_status_fn=get_request_status,
        get_tracker_fn=get_tracker,
        list_tracked_root_ids_fn=list_tracked_root_ids,
        format_task_status_fn=format_task_status,
        boot_summary=boot_summary,
        runtimes=runtimes,
        default_claim_ttl_sec=DEFAULT_CLAIM_TTL_SEC,
        default_request_timeout_sec=DEFAULT_REQUEST_TIMEOUT_SEC,
        diagnostics_format_fn=format_diagnostics,
        agent_id_to_role=agent_id_to_role,
    )

    logger.info("Shutting down runtimes...")
    for rt in runtimes:
        await rt.stop()
    logger.info("Exiting.")


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
