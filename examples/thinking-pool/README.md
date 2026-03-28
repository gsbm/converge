# Advanced Thinking Pool Example

This example demonstrates a **multi-agent collaborative reasoning pool** using the `converge` library: heterogeneous agents with distinct roles, parallel capability-scoped subtasks, coordination protocols, and a **menu-driven CLI** with commands for observability and recovery.

## Architecture Overview

- **User** submits a prompt via the CLI (menu or command). The system creates one **root task** and several **subtasks** with different `required_capabilities` (research, critique, synthesize, verify) so the right agents see the right work.
- **Agents** run in parallel, each with its own `AgentRuntime`. They claim subtasks, execute, and report results. Coordination uses shared `NegotiationProtocol`, `DelegationProtocol`, `BiddingProtocol`, and `votes_store`.
- **Observability**: each request has a tracker (stage, subtasks, events). The CLI offers a **main menu**, **request dashboard**, **live watch**, **event timeline**, **agent pool**, and **diagnostics**.

## Menu-First UX

On startup you see a **boot summary** (pool ID, providers, agents started, protocols) and the **main menu**:

```
--- Thinking Pool ---
  Pool ID: ...
  Providers: openai
  Agents:   5/5 started
  Protocols: ok
----------------------

  ================
    Thinking Pool
  ================
  Current request: (none)

  1. Submit New Request
  2. View Request Dashboard
  3. Live Watch Request
  4. Explore Timeline Events
  5. Inspect Agent Pool
  6. System Health & Diagnostics
  7. Export Session Artifacts
  8. Help
  0. Exit

  Or type a command: submit, status, watch, agents, events, requests, exit
  Shortcuts: s, st, w, a, e, r, h, ?
```

- **Numbered choices (0–9)**: Press a number to run that action. After **1 (Submit)** you are prompted for a prompt; the new request becomes the **current request** and its dashboard is shown.
- **Request navigation**: Use **2 (Dashboard)** with no argument to list recent requests as `#1`, `#2`, … Then use **status #1**, **watch #2**, **events #1** to target by index instead of pasting UUIDs.
- **Current request**: After submit, `status`, `watch`, and `events` without an argument use the current request.
- **Command mode**: Type `cmd` to switch to a raw command prompt; type `menu` to return to the menu.

## Commands and Shortcuts

| Command     | Shortcut | Description |
|------------|----------|-------------|
| `submit <prompt>` | `s` | Submit a new request. Creates root + subtasks. |
| `status [id\|#N]` | `st` | Show request dashboard. Omit id to use current or list recent. |
| `watch [id\|#N]`  | `w` | Live follow until terminal state or timeout. |
| `events [id\|#N]` | `e` | Show event timeline for the request. |
| `agents`         | `a` | List pool agents with role labels. |
| `requests`       | `r` | List recent requests with index and stage. |
| `dashboard [id\|#N]` | `d` | Open dashboard for a request. |
| `diagnostics`    | `diag` | System health, runtime status, pending count. |
| `fail [id\|#N]`  | — | Mark a request as failed (user-driven). |
| `export`         | — | Export replay log to `thinking_pool_replay.json`. |
| `menu` / `cmd`   | `m` | Toggle menu vs command mode. |
| `help` / `?`     | `h`, `?` | Show command cheat sheet. |
| `exit` / `quit` / `q` | `q` | Exit and export replay. |

## First-Run Flow

1. Run the app (see [Running](#running-the-example)).
2. At the menu, press **1** (or type `submit` and a prompt).
3. Enter a prompt when asked; the request is submitted and the **Request Dashboard** is shown.
4. Use **3** (or `watch`) to follow progress until completion, or **2** / **status** to refresh the dashboard.
5. Use **4** / **events** to see the event timeline, **5** / **agents** to see the pool with roles.
6. Use **6** / **diagnostics** if something looks wrong (e.g. 0 agents, tasks stuck).

## Recovery and Diagnostics

- **Tasks never complete**: Run **6 (Diagnostics)** to see agent count, runtime health, and pending task count. Ensure API keys are set and [llm] extras are installed. Use **status #N** to see which subtasks are pending/assigned.
- **Degraded boot**: If the boot banner shows `[!] Degraded`, run **6** for details and check providers and agent startup logs.
- **User-driven failure**: To close a request without waiting, use **fail &lt;task_id&gt;** or **fail #N**.
- **Replay**: On exit, a replay log is written to `thinking_pool_replay.json` in the current directory (and via **7** / **export** anytime).

## Role Catalog

| Role         | Capabilities   | Description |
|-------------|----------------|-------------|
| Planner     | plan, coordinate | Decomposes requests, proposes subtasks. |
| Researcher  | research       | Explores options, reports findings. |
| Critic      | critique       | Stress-tests ideas, finds gaps. |
| Synthesizer | synthesize     | Merges inputs into a coherent plan. |
| Verifier    | verify         | Checks completeness; can vote. |

## Setup & Requirements

- Python 3.11+
- Install converge with LLM extras:

```bash
pip install -e ".[llm,llm-anthropic,llm-mistral,python-dotenv]"
```

- Set at least one provider API key:

```bash
export OPENAI_API_KEY="sk-..."
# and/or
export ANTHROPIC_API_KEY="sk-ant-..."
export MISTRAL_API_KEY="..."
```

## Running the Example

From the project root:

```bash
PYTHONPATH=. python examples/thinking-pool/main.py
```

Or with the package installed:

```bash
python examples/thinking-pool/main.py
```

## Configuration

- **Provider / model**: First available of OpenAI, Anthropic, Mistral. Override with `POOL_MODEL` (e.g. `gpt-4o-mini`).
- **Claim TTL**: Tasks use `claim_ttl_sec` (default 120s); runtimes run `release_expired_claims` periodically.
- **Request timeout**: `watch` times out after 180s and marks the root task failed.

See `orchestration.py` and `main.py` for constants.

## Agent Behavior (Advanced)

The converge LLM agent and runtime support several optional behaviors:

- **ReAct-style tool loop**: When agents emit `InvokeTool`, the runtime runs the tool, feeds the result back as `tool_observations`, and re-calls `decide()` until no more tools or a terminal decision. Configure with `max_tool_loop_iterations` on `AgentRuntime` (default 5; set 0 to disable).
- **Structured output**: Use `use_structured_output=True` on `LLMAgent` to request provider-native function/tool calling for the decision array (OpenAI, Anthropic, Mistral).
- **Reflection**: Pass `reflect_result=(task_id, result) -> revised result` to `StandardExecutor` (e.g. via `executor_kwargs`) to run a review step before committing `ReportTask`.
- **Conversation history**: Pass a `ShortTermMemory` (or object with `append(role, content)` and `get_messages()`) as `memory=` to `LLMAgent` to retain context across turns; history is trimmed by message count.
- **Retry**: The LLM agent retries provider calls (2 retries, exponential backoff) on rate limit/timeout/503. Use `on_decide_error=callable` for observability when decide fails.
- **Few-shot**: Pass `few_shot_examples=[(user_content, assistant_json), ...]` to `LLMAgent` to inject up to 2 example turns into the prompt.

## File Layout

- `main.py` — Entry point, pool setup, protocol wiring, agent creation, controller entry.
- `cli_controller.py` — Menu and command dispatch, app state, current request.
- `cli_parser.py` — Command parsing, aliases, quoted args, `#N` resolution.
- `cli_views.py` — Menu, dashboard, watch, events, agents, help formatting.
- `diagnostics.py` — Boot summary and diagnostics view.
- `roles.py` — Role definitions (capabilities, prompts).
- `orchestration.py` — Request submission and status.
- `events.py` — Request tracking, timeline, filters.

## References

- [Converge coordination API](../docs/api/coordination.md)
- [Customization — Protocol lifecycle](../docs/user_guide/customization.md#protocol-lifecycle-and-wiring)
- [Observability](../docs/api/observability.md)

## Validation

```bash
pytest tests/integration/test_thinking_pool_example.py -v
```

Tests verify orchestration, request tracking, and role configs.
