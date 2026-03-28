"""Integration tests for the advanced thinking-pool example (orchestration, events, roles)."""

import sys
from pathlib import Path

import pytest

# Add example directory so we can import events, orchestration, roles (run from repo root)
_EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "thinking-pool"
if _EXAMPLE_DIR.exists() and str(_EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLE_DIR))


@pytest.fixture(scope="module")
def example_modules():
    """Import example modules (events, orchestration, roles) after path is set."""
    import events as ev
    import orchestration as orch
    import roles as r
    return {"events": ev, "orchestration": orch, "roles": r}


@pytest.fixture(scope="module")
def cli_modules():
    """Import CLI modules after path is set."""
    import cli_parser as parser
    import cli_views as views
    import diagnostics as diag
    return {"parser": parser, "views": views, "diagnostics": diag}


@pytest.mark.asyncio
async def test_thinking_pool_submit_request_creates_root_and_subtasks(example_modules):
    """submit_request creates one root task and four capability-scoped subtasks."""
    from converge.coordination.pool_manager import PoolManager
    from converge.coordination.task_manager import TaskManager
    from converge.extensions.storage.memory import MemoryStore
    from converge.policy.admission import OpenAdmission

    store = MemoryStore()
    pm = PoolManager(store=store)
    tm = TaskManager(store=store)
    pool = pm.create_pool({"topics": [], "admission_policy": OpenAdmission()})
    orch = example_modules["orchestration"]

    root_id, subtask_ids = orch.submit_request(tm, pool.id, "Test prompt", claim_ttl_sec=30.0)

    assert root_id
    assert len(subtask_ids) == 4
    root = tm.get_task(root_id)
    assert root is not None
    assert root.objective.get("type") == "root_request"
    assert root.objective.get("prompt") == "Test prompt"
    for sid in subtask_ids:
        t = tm.get_task(sid)
        assert t is not None
        assert t.pool_id == pool.id
        assert len(t.required_capabilities) == 1
        assert t.required_capabilities[0] in ("research", "critique", "synthesize", "verify")
        assert t.constraints.get("claim_ttl_sec") == 30.0


@pytest.mark.asyncio
async def test_thinking_pool_request_tracker_stage_and_events(example_modules):
    """Request tracker has parallel_execution stage and records events."""
    from converge.coordination.pool_manager import PoolManager
    from converge.coordination.task_manager import TaskManager
    from converge.extensions.storage.memory import MemoryStore
    from converge.policy.admission import OpenAdmission

    store = MemoryStore()
    pm = PoolManager(store=store)
    tm = TaskManager(store=store)
    pool = pm.create_pool({"topics": [], "admission_policy": OpenAdmission()})
    orch = example_modules["orchestration"]
    ev = example_modules["events"]

    root_id, subtask_ids = orch.submit_request(tm, pool.id, "Another test", claim_ttl_sec=10.0)
    tracker = ev.get_tracker(root_id)

    assert tracker.stage.value == "parallel_execution"
    assert tracker.root_task_id == root_id
    assert set(tracker.subtask_ids) == set(subtask_ids)
    assert len(tracker.events) >= 3  # submitted, subtask_created x4, stage
    event_kinds = [e.kind for e in tracker.events]
    assert "submitted" in event_kinds
    assert "stage" in event_kinds


@pytest.mark.asyncio
async def test_thinking_pool_get_request_status_structure(example_modules):
    """get_request_status returns root_task, subtasks, stage, events_count."""
    from converge.coordination.pool_manager import PoolManager
    from converge.coordination.task_manager import TaskManager
    from converge.extensions.storage.memory import MemoryStore
    from converge.policy.admission import OpenAdmission

    store = MemoryStore()
    pm = PoolManager(store=store)
    tm = TaskManager(store=store)
    pool = pm.create_pool({"topics": [], "admission_policy": OpenAdmission()})
    orch = example_modules["orchestration"]

    root_id, _ = orch.submit_request(tm, pool.id, "Status test", claim_ttl_sec=5.0)
    status = orch.get_request_status(tm, root_id)

    assert status["root_task_id"] == root_id
    assert status["stage"] == "parallel_execution"
    assert status["root_task"] is not None
    assert len(status["subtasks"]) == 4
    assert status["events_count"] >= 1
    for st in status["subtasks"]:
        assert "id" in st and "state" in st
        assert st["state"] in ("pending", "assigned", "completed", "failed", "cancelled")


def test_thinking_pool_roles_have_capabilities(example_modules):
    """Roles define capabilities and prompts."""
    r = example_modules["roles"]
    configs = r.default_role_configs(provider="openai", model="gpt-4o-mini")
    assert len(configs) >= 4
    caps_seen = set()
    for c in configs:
        assert "name" in c and "prompt" in c and "capabilities" in c
        caps_seen.update(c["capabilities"])
    assert "research" in caps_seen
    assert "critique" in caps_seen
    assert "synthesize" in caps_seen
    assert "verify" in caps_seen


def test_cli_parser_aliases(cli_modules):
    """Parser resolves aliases."""
    p = cli_modules["parser"]
    parsed = p.parse_line("s hello")
    assert parsed.command == "submit"
    assert parsed.rest == "hello"
    parsed = p.parse_line("q")
    assert parsed.command == "exit"


def test_cli_parser_menu_number(cli_modules):
    """Parser treats single digit as menu choice."""
    p = cli_modules["parser"]
    parsed = p.parse_line("0")
    assert parsed.is_menu_number is True
    assert parsed.menu_index == 0


def test_cli_parser_index_ref(cli_modules):
    """Parser resolves #N to recent request id (list is newest-first; #1 = most recent)."""
    p = cli_modules["parser"]
    recent = ["id-second", "id-first"]  # newest first, as from get_recent_for_parser()
    parsed = p.parse_line("status #1", recent_request_ids=recent)
    assert parsed.command == "status"
    assert parsed.rest == "id-second"


def test_diagnostics_boot_summary(cli_modules):
    """Diagnostics build and format boot summary."""
    d = cli_modules["diagnostics"]
    avail = d.check_provider_availability()
    assert isinstance(avail, dict)
    summary = d.get_boot_summary(
        provider_available=avail,
        agents_started=3,
        agents_expected=5,
        pool_id="test-pool",
        protocols_wired=True,
    )
    assert summary["pool_id"] == "test-pool"
    lines = d.format_boot_banner(summary)
    assert any("test-pool" in line for line in lines)


def test_cli_views_menu(cli_modules):
    """Views render main menu."""
    v = cli_modules["views"]
    menu_lines = v.render_main_menu()
    assert any("Submit" in line for line in menu_lines)
    assert any("Exit" in line for line in menu_lines)


def test_controller_app_state():
    """AppState tracks current request and recent list."""
    from cli_controller import AppState
    state = AppState()
    assert state.current_request_id is None
    state.set_current("req-1")
    assert state.current_request_id == "req-1"
    state.set_current("req-2")
    recent = state.get_recent_for_parser()
    assert recent[0] == "req-2"
    assert recent[1] == "req-1"
