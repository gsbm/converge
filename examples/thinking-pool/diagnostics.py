"""
Boot-time and runtime diagnostics for the thinking-pool demo.
Health snapshot, provider availability, protocol wiring, and actionable failure hints.
"""

import logging
import os
from typing import Any

logger = logging.getLogger("thinking_pool.diagnostics")


def check_provider_availability() -> dict[str, bool]:
    """Return which LLM providers are available (API key set)."""
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mistral": bool(os.getenv("MISTRAL_API_KEY")),
    }


def get_boot_summary(
    provider_available: dict[str, bool],
    agents_started: int,
    agents_expected: int,
    pool_id: str,
    *,
    protocols_wired: bool = True,
) -> dict[str, Any]:
    """Build a boot summary for display. Call after pool and agents are created."""
    return {
        "providers": provider_available,
        "agents_started": agents_started,
        "agents_expected": agents_expected,
        "pool_id": pool_id,
        "protocols_wired": protocols_wired,
        "degraded": agents_started < agents_expected or not any(provider_available.values()),
    }


def format_boot_banner(summary: dict[str, Any]) -> list[str]:
    """Format boot summary as lines for CLI display."""
    lines = []
    lines.append("--- Thinking Pool ---")
    lines.append(f"  Pool ID: {summary['pool_id']}")
    providers = summary.get("providers", {})
    available = [k for k, v in providers.items() if v]
    lines.append(f"  Providers: {', '.join(available) or 'none'}")
    lines.append(f"  Agents:   {summary['agents_started']}/{summary['agents_expected']} started")
    lines.append(f"  Protocols: {'ok' if summary.get('protocols_wired') else 'not wired'}")
    if summary.get("degraded"):
        lines.append("  [!] Degraded: run 'diagnostics' or '6' for details.")
    lines.append("----------------------")
    return lines


def format_diagnostics(
    summary: dict[str, Any],
    runtimes: list[Any] | None = None,
    task_manager: Any | None = None,
) -> list[str]:
    """Format full diagnostics view (boot summary + runtime health + pending counts)."""
    lines = []
    lines.append("=== System Health & Diagnostics ===")
    lines.extend(format_boot_banner(summary))
    if runtimes:
        healthy = sum(1 for r in runtimes if getattr(r, "is_healthy", lambda: True)())
        lines.append(f"  Runtime health: {healthy}/{len(runtimes)} healthy")
    if task_manager is not None and hasattr(task_manager, "pending_task_ids"):
        n = len(getattr(task_manager, "pending_task_ids", []))
        lines.append(f"  Pending tasks:  {n}")
    lines.append("  Hint: If agents are 0 or tasks never complete, check API keys and install [llm] extras.")
    lines.append("====================================")
    return lines
