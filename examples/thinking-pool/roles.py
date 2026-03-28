"""
Role definitions for the advanced thinking pool: capabilities, topic affinity, and prompt contracts.
Used for heterogeneous agent behavior and task routing (required_capabilities, topic, priority).
"""

from dataclasses import dataclass, field
from typing import Any

# Capability names used for task routing; agents declare these, tasks require them.
CAP_PLAN = "plan"
CAP_RESEARCH = "research"
CAP_CRITIQUE = "critique"
CAP_SYNTHESIZE = "synthesize"
CAP_VERIFY = "verify"
CAP_COORDINATE = "coordinate"

# Topic namespaces for optional topic-scoped routing.
TOPIC_PLANNING = "planning"
TOPIC_RESEARCH = "research"
TOPIC_CRITIQUE = "critique"
TOPIC_SYNTHESIS = "synthesis"
TOPIC_VERIFICATION = "verification"


@dataclass
class RoleSpec:
    """Specification for one pool role: display name, capabilities, topic, prompt, and optional reasoning hint."""
    name: str
    capabilities: list[str] = field(default_factory=list)
    topic_namespace: str | None = None
    prompt: str = ""
    reasoning_hint: str = ""


# Role catalog with explicit behavior contracts.
ROLES: list[RoleSpec] = [
    RoleSpec(
        name="Planner",
        capabilities=[CAP_PLAN, CAP_COORDINATE],
        topic_namespace=TOPIC_PLANNING,
        prompt=(
            "You are a Planner. You decompose high-level requests into clear, prioritized subtasks. "
            "When you see a task with a user prompt, use SubmitTask to create subtasks with explicit "
            "objectives and required_capabilities (research, critique, synthesize, verify). "
            "Use Propose with session_id for decomposition proposals when coordination is needed. "
            "You may ClaimTask only for planning-type tasks; delegate execution to specialists via Delegate or "
            "by creating subtasks they can claim. Output ONLY a valid JSON array of decisions."
        ),
    ),
    RoleSpec(
        name="Researcher",
        capabilities=[CAP_RESEARCH],
        topic_namespace=TOPIC_RESEARCH,
        reasoning_hint="Think step by step; use tools to verify before reporting when available.",
        prompt=(
            "You are a Researcher. You explore alternatives, gather evidence, and produce structured findings. "
            "Claim tasks that require research capability. ReportTask with a clear result (findings, sources, options). "
            "You may SendMessage to share partial results with others. Output ONLY a valid JSON array of decisions."
        ),
    ),
    RoleSpec(
        name="Critic",
        capabilities=[CAP_CRITIQUE],
        topic_namespace=TOPIC_CRITIQUE,
        reasoning_hint="Consider edge cases and counterexamples before concluding.",
        prompt=(
            "You are a Critic. You stress-test ideas, find flaws, edge cases, and inconsistencies. "
            "Claim tasks that require critique capability. ReportTask with structured feedback (risks, gaps, suggestions). "
            "You may SendMessage to request clarification. Output ONLY a valid JSON array of decisions."
        ),
    ),
    RoleSpec(
        name="Synthesizer",
        capabilities=[CAP_SYNTHESIZE],
        topic_namespace=TOPIC_SYNTHESIS,
        prompt=(
            "You are a Synthesizer. You merge multiple inputs into a coherent narrative, plan, or recommendation. "
            "Claim tasks that require synthesize capability. ReportTask with a unified summary and clear conclusions. "
            "You may SendMessage to ask for missing inputs. Output ONLY a valid JSON array of decisions."
        ),
    ),
    RoleSpec(
        name="Verifier",
        capabilities=[CAP_VERIFY],
        topic_namespace=TOPIC_VERIFICATION,
        reasoning_hint="Check each requirement explicitly; output pass/fail with evidence.",
        prompt=(
            "You are a Verifier. You check completeness, consistency, and constraints before finalization. "
            "Claim tasks that require verify capability. ReportTask with pass/fail and a short checklist. "
            "You may Vote when a vote_id is provided for acceptance. Output ONLY a valid JSON array of decisions."
        ),
    ),
]


def get_role_by_name(name: str) -> RoleSpec | None:
    """Return the RoleSpec for a given display name, or None."""
    for r in ROLES:
        if r.name == name:
            return r
    return None


def get_roles_by_capability(cap: str) -> list[RoleSpec]:
    """Return all roles that have the given capability."""
    return [r for r in ROLES if cap in r.capabilities]


def default_role_configs(provider: str = "openai", model: str | None = None) -> list[dict[str, Any]]:
    """
    Build a list of role config dicts for agent creation: name, provider, model, prompt, capabilities, topic_namespace.
    One entry per role; caller can filter or duplicate (e.g. multiple Researchers) by provider availability.
    """
    model = model or "gpt-4o-mini"
    return [
        {
            "name": r.name,
            "provider": provider,
            "model": model,
            "prompt": (f"{r.reasoning_hint} " + r.prompt).strip() if r.reasoning_hint else r.prompt,
            "capabilities": r.capabilities,
            "topic_namespace": r.topic_namespace,
        }
        for r in ROLES
    ]
