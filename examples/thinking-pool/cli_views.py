"""
CLI view formatting: menu, dashboard, watch, events, agents, diagnostics.
Plain ASCII output; optional rich mode can be added later.
"""

from collections.abc import Callable
from typing import Any


def truncate_id(s: str, head: int = 24) -> str:
    """Consistent ID truncation for display."""
    if not s:
        return "-"
    return s[:head] + "..." if len(s) > head else s


def header(title: str, char: str = "=") -> str:
    return f"{char * (min(len(title) + 4, 60))}\n  {title}\n{char * (min(len(title) + 4, 60))}"


def section(title: str) -> str:
    return f"\n--- {title} ---"


def hint_line(hints: list[str]) -> str:
    return "  " + "  ".join(f"[{h}]" for h in hints)


# --- Main menu ---
MAIN_MENU_LINES = [
    "",
    "  1. Submit New Request",
    "  2. View Request Dashboard",
    "  3. Live Watch Request",
    "  4. Explore Timeline Events",
    "  5. Inspect Agent Pool",
    "  6. System Health & Diagnostics",
    "  7. Export Session Artifacts",
    "  8. Help",
    "  0. Exit",
    "",
    "  Or type a command: submit, status, watch, agents, events, requests, exit",
    "  Shortcuts: s, st, w, a, e, r, h, ?",
]


def render_main_menu(current_request_id: str | None = None) -> list[str]:
    lines = [header("Thinking Pool", "-")]
    if current_request_id:
        lines.append(f"  Current request: {truncate_id(current_request_id, 20)}")
    lines.extend(MAIN_MENU_LINES)
    lines.append(hint_line(["#0-9", "command", "?"]))
    return lines


# --- Request list (for picker) ---
def render_request_list(
    request_ids: list[str],
    get_stage: Callable[[str], str],
    max_entries: int = 20,
) -> list[str]:
    lines = [section("Recent Requests")]
    if not request_ids:
        lines.append("  No requests yet. Submit a prompt first (1 or submit <prompt>).")
        return lines
    for i, rid in enumerate(list(reversed(request_ids))[:max_entries], 1):
        stage = get_stage(rid)
        lines.append(f"  #{i}  {truncate_id(rid, 24)}  stage={stage}")
    lines.append("  Use: status #N, watch #N, events #N, or full task_id")
    return lines


# --- Dashboard (single request) ---
def render_dashboard(
    root_task_id: str,
    status: dict[str, Any],
    task_status_formatter: Callable[[Any], str],
) -> list[str]:
    lines = []
    lines.append(header("Request Dashboard", "-"))
    lines.append(f"  Request: {truncate_id(root_task_id, 28)}")
    lines.append(f"  Stage:   {status.get('stage', '?')}  |  Events: {status.get('events_count', 0)}")
    root = status.get("root_task")
    if root:
        lines.append(section("Root Task"))
        lines.append(task_status_formatter(root))
    subtasks = status.get("subtasks", [])
    if subtasks:
        lines.append(section("Subtasks"))
        by_state: dict[str, list[dict]] = {}
        for st in subtasks:
            s = st.get("state", "?")
            by_state.setdefault(s, []).append(st)
        for state in ("pending", "assigned", "completed", "failed", "cancelled"):
            if state not in by_state:
                continue
            for st in by_state[state]:
                sid = st.get("id", "?")
                lines.append(f"    [{state}] {truncate_id(sid, 16)}  assigned_to={truncate_id(str(st.get('assigned_to') or '-'), 12)}")
    lines.append("")
    lines.append(hint_line(["W]atch", "E]vents", "B]ack"]))
    return lines


# --- Watch progress ---
def render_watch_tick(
    elapsed: float,
    status: dict[str, Any],
    total: int,
    completed: int,
) -> str:
    states = [s.get("state", "?") for s in status.get("subtasks", [])]
    done = sum(1 for x in states if x == "completed")
    bar = f"[{done}/{total}]" if total else ""
    return f"  [{elapsed:.0f}s] {bar} " + " ".join(states)


# --- Events ---
def render_events(event_lines: list[str], limit: int = 30, kind_filter: str | None = None) -> list[str]:
    lines = [section("Timeline Events")]
    if kind_filter:
        lines.append(f"  Filter: kind={kind_filter}")
    for line in event_lines[-limit:]:
        if kind_filter and f" {kind_filter}" not in line and not line.strip().startswith(kind_filter):
            continue
        lines.append("  " + line)
    return lines


# --- Agents ---
def render_agents(
    member_ids: list[str],
    agent_id_to_role: dict[str, str] | None = None,
) -> list[str]:
    lines = [section("Agent Pool")]
    if not member_ids:
        lines.append("  No agents in pool.")
        return lines
    for i, aid in enumerate(member_ids, 1):
        role = (agent_id_to_role or {}).get(aid, "")
        if role:
            lines.append(f"  {i}. {truncate_id(aid, 22)}  ({role})")
        else:
            lines.append(f"  {i}. {truncate_id(aid, 22)}")
    return lines


# --- Help ---
HELP_LINES = [
    "  submit <prompt>   Submit a new request (s <prompt>)",
    "  status [id|#N]    Show request status (st)",
    "  watch [id|#N]     Live follow until done (w)",
    "  events [id|#N]    Show event timeline (e)",
    "  agents            List pool agents (a)",
    "  requests          List recent requests (r)",
    "  dashboard [id|#N] Open dashboard for request (d)",
    "  diagnostics       System health (diag)",
    "  menu              Show main menu (m)",
    "  exit / quit / q   Exit and export replay",
    "  ? / h             This help",
]


def render_help() -> list[str]:
    lines = [header("Help", "-")]
    lines.extend(HELP_LINES)
    return lines
