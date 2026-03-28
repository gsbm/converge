"""
CLI controller: app state, menu routing, current-request context, and command dispatch.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("thinking_pool.controller")


class AppState:
    """Holds current request context and recent request ids for navigation."""
    def __init__(self):
        self.current_request_id: str | None = None
        self.recent_request_ids: list[str] = []
        self.menu_mode: bool = True  # True = show menu prompt, False = raw command prompt
        self._max_recent = 50

    def set_current(self, root_id: str) -> None:
        self.current_request_id = root_id
        if root_id not in self.recent_request_ids:
            self.recent_request_ids.append(root_id)
        else:
            self.recent_request_ids.remove(root_id)
            self.recent_request_ids.append(root_id)
        self.recent_request_ids = self.recent_request_ids[-self._max_recent :]

    def get_recent_for_parser(self) -> list[str]:
        """Most recent first for #1, #2, ... indexing."""
        return list(reversed(self.recent_request_ids))


async def run_controller(
    task_manager: Any,
    pool_id: str,
    pool_manager: Any,
    replay_log: Any,
    submit_request_fn: Any,
    get_request_status_fn: Any,
    get_tracker_fn: Any,
    list_tracked_root_ids_fn: Any,
    format_task_status_fn: Any,
    boot_summary: dict[str, Any],
    runtimes: list[Any],
    default_claim_ttl_sec: float,
    default_request_timeout_sec: float,
    diagnostics_format_fn: Any,
    agent_id_to_role: dict[str, str] | None = None,
) -> None:
    """
    Run the interactive REPL with menu and command mode. Runs until exit.
    """
    from cli_parser import parse_line
    from cli_views import (
        render_agents,
        render_dashboard,
        render_events,
        render_help,
        render_main_menu,
        render_request_list,
        render_watch_tick,
    )

    state = AppState()

    def get_stage(rid: str) -> str:
        try:
            tr = get_tracker_fn(rid)
            return tr.stage.value
        except Exception:
            return "?"

    def _read_input() -> str:
        if state.menu_mode:
            return input("\n[thinking-pool] Choice or command (0-9, command, ?): ").strip()
        return input("\n[thinking-pool] Command: ").strip()

    # Initial menu
    for line in render_main_menu(state.current_request_id):
        print(line)

    while True:
        try:
            line = await asyncio.to_thread(_read_input)
            line = line.strip()
            if not line:
                if state.menu_mode:
                    for out_line in render_main_menu(state.current_request_id):
                        print(out_line)
                continue

            recent = state.get_recent_for_parser()
            parsed = parse_line(line, recent_request_ids=recent)

            if parsed.suggestion:
                print(f"  Unknown command '{parsed.command}'. {parsed.suggestion}")
                continue
            if parsed.command not in (
                "submit", "status", "watch", "agents", "events", "exit", "help",
                "requests", "dashboard", "diagnostics", "menu", "cmd", "export", "fail",
            ) and not (parsed.command == "menu" and parsed.is_menu_number):
                print("  Unknown command. Type ? or help.")
                continue

            # Menu number dispatch
            if parsed.command == "menu" and parsed.is_menu_number and parsed.menu_index is not None:
                n = parsed.menu_index
                if n == 0:
                    break
                if n == 1:
                    prompt = await asyncio.to_thread(
                        lambda: input("  Enter prompt: ").strip(),
                    )
                    if not prompt:
                        print("  No prompt entered.")
                        continue
                    root_id, _ = submit_request_fn(task_manager, pool_id, prompt, claim_ttl_sec=default_claim_ttl_sec)
                    state.set_current(root_id)
                    print(f"  Submitted. root_task_id={root_id}")
                    for out_line in render_dashboard(root_id, get_request_status_fn(task_manager, root_id), format_task_status_fn):
                        print(out_line)
                    continue
                if n == 2:
                    rid = parsed.rest or state.current_request_id
                    if not rid:
                        ids = list_tracked_root_ids_fn()
                        if not ids:
                            print("  No requests. Submit first (1).")
                            continue
                        for out_line in render_request_list(ids, get_stage):
                            print(out_line)
                        continue
                    status = get_request_status_fn(task_manager, rid)
                    for out_line in render_dashboard(rid, status, format_task_status_fn):
                        print(out_line)
                    continue
                if n == 3:
                    rid = parsed.rest or state.current_request_id
                    if not rid:
                        print("  Usage: watch <task_id> or watch #N. Or set current request via dashboard (2).")
                        continue
                    await _run_watch(
                        task_manager, rid, get_request_status_fn, get_tracker_fn,
                        render_watch_tick, format_task_status_fn, default_request_timeout_sec,
                    )
                    continue
                if n == 4:
                    rid = parsed.rest or state.current_request_id
                    if not rid:
                        print("  Usage: events <task_id> or events #N.")
                        continue
                    tr = get_tracker_fn(rid)
                    for out_line in render_events(tr.format_events(limit=30)):
                        print(out_line)
                    continue
                if n == 5:
                    pool_obj = pool_manager.get_pool(pool_id)
                    members = list(getattr(pool_obj, "agents", [])) if pool_obj else []
                    for out_line in render_agents(members, agent_id_to_role or {}):
                        print(out_line)
                    continue
                if n == 6:
                    for out_line in diagnostics_format_fn(boot_summary, runtimes, task_manager):
                        print(out_line)
                    continue
                if n == 7:
                    if replay_log:
                        out = Path.cwd() / "thinking_pool_replay.json"
                        try:
                            replay_log.export(str(out))
                            print(f"  Exported replay to {out}")
                        except Exception as e:
                            print(f"  Export failed: {e}")
                    else:
                        print("  Replay log not available.")
                    continue
                if n == 8:
                    for out_line in render_help():
                        print(out_line)
                    continue
                for out_line in render_main_menu(state.current_request_id):
                    print(out_line)
                continue

            # Command dispatch
            if parsed.command == "exit":
                break
            if parsed.command == "cmd":
                state.menu_mode = False
                print("  Command mode. Type 'menu' to return to menu.")
                continue
            if parsed.command == "menu":
                state.menu_mode = True
                for out_line in render_main_menu(state.current_request_id):
                    print(out_line)
                continue
            if parsed.command == "help":
                for out_line in render_help():
                    print(out_line)
                continue
            if parsed.command == "submit":
                prompt = parsed.rest
                if not prompt:
                    prompt = await asyncio.to_thread(lambda: input("  Prompt: ").strip())
                if not prompt:
                    print("  Usage: submit <prompt>")
                    continue
                root_id, _ = submit_request_fn(task_manager, pool_id, prompt, claim_ttl_sec=default_claim_ttl_sec)
                state.set_current(root_id)
                print(f"  Submitted. root_task_id={root_id}")
                continue
            if parsed.command == "requests":
                ids = list_tracked_root_ids_fn()
                for out_line in render_request_list(ids, get_stage):
                    print(out_line)
                continue
            if parsed.command == "status" or parsed.command == "dashboard":
                rid = parsed.rest or state.current_request_id
                if not rid:
                    print("  Usage: status <task_id> or status #N. Or submit first.")
                    continue
                status = get_request_status_fn(task_manager, rid)
                for out_line in render_dashboard(rid, status, format_task_status_fn):
                    print(out_line)
                continue
            if parsed.command == "watch":
                rid = parsed.rest or state.current_request_id
                if not rid:
                    print("  Usage: watch <task_id> or watch #N.")
                    continue
                await _run_watch(
                    task_manager, rid, get_request_status_fn, get_tracker_fn,
                    render_watch_tick, format_task_status_fn, default_request_timeout_sec,
                )
                continue
            if parsed.command == "agents":
                pool_obj = pool_manager.get_pool(pool_id)
                members = list(getattr(pool_obj, "agents", [])) if pool_obj else []
                for out_line in render_agents(members, agent_id_to_role or {}):
                    print(out_line)
                continue
            if parsed.command == "events":
                rid = parsed.rest or state.current_request_id
                if not rid:
                    print("  Usage: events <task_id> or events #N.")
                    continue
                tr = get_tracker_fn(rid)
                for out_line in render_events(tr.format_events(limit=30)):
                    print(out_line)
                continue
            if parsed.command == "diagnostics":
                for out_line in diagnostics_format_fn(boot_summary, runtimes, task_manager):
                    print(out_line)
                continue
            if parsed.command == "fail":
                rid = parsed.rest or state.current_request_id
                if not rid:
                    print("  Usage: fail <task_id> or fail #N.")
                    continue
                try:
                    task_manager.fail_task(rid, reason={"user_requested": True})
                    print(f"  Request {rid[:20]}... marked failed.")
                except Exception as e:
                    print(f"  Fail failed: {e}")
                continue
            if parsed.command == "export":
                if replay_log:
                    out = Path.cwd() / "thinking_pool_replay.json"
                    try:
                        replay_log.export(str(out))
                        print(f"  Exported to {out}")
                    except Exception as e:
                        print(f"  Export failed: {e}")
                else:
                    print("  Replay not available.")
                continue

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            logger.exception("REPL error: %s", e)
            print(f"  Error: {e}")

    if replay_log:
        out = Path.cwd() / "thinking_pool_replay.json"
        try:
            replay_log.export(str(out))
            print(f"Replay log exported to {out}")
        except Exception:
            pass


async def _run_watch(
    task_manager: Any,
    task_id: str,
    get_request_status_fn: Any,
    get_tracker_fn: Any,
    render_watch_tick_fn: Any,
    format_task_status_fn: Any,
    timeout: float,
    *,
    delta_only: bool = False,
) -> None:
    interval = 2.0
    elapsed = 0.0
    last_states: tuple[str, ...] | None = None
    while elapsed < timeout:
        status = get_request_status_fn(task_manager, task_id)
        root = status.get("root_task")
        terminal = root is not None and root.state.value in ("completed", "failed", "cancelled")
        subtasks = status.get("subtasks", [])
        states = tuple(s.get("state", "?") for s in subtasks)
        total = len(subtasks)
        completed = sum(1 for s in subtasks if s.get("state") == "completed")
        if terminal and root is not None:
            print(f"\n  [Done] state={root.state.value}")
            if getattr(root, "result", None) is not None:
                print("  Result:", root.result)
            return
        if not delta_only or last_states is None or states != last_states:
            print(render_watch_tick_fn(elapsed, status, total, completed))
        last_states = states
        await asyncio.sleep(interval)
        elapsed += interval
    print("  Timeout.")
    root = task_manager.get_task(task_id)
    if root is not None and root.state.value not in ("completed", "failed", "cancelled"):
        try:
            task_manager.fail_task(task_id, reason={"timeout": True, "elapsed_sec": elapsed})
            print("  Root task marked failed (timeout).")
        except Exception:
            pass
