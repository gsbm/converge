"""
CLI command parsing: tokenization, aliases, quoted args, and multiline prompt handling.
"""

from dataclasses import dataclass

# Canonical commands and aliases (alias -> canonical).
ALIASES = {
    "s": "submit",
    "st": "status",
    "w": "watch",
    "a": "agents",
    "e": "events",
    "h": "help",
    "?": "help",
    "q": "exit",
    "quit": "exit",
    "r": "requests",
    "d": "dashboard",
    "diag": "diagnostics",
    "m": "menu",
    "cmd": "cmd",
}
CANONICAL_COMMANDS = frozenset({
    "submit", "status", "watch", "agents", "events", "exit", "help",
    "requests", "dashboard", "diagnostics", "menu", "cmd", "export", "retry", "fail",
})


@dataclass
class ParsedCommand:
    """Result of parsing one user input line."""
    command: str
    rest: str
    is_menu_number: bool = False
    menu_index: int | None = None
    suggestion: str | None = None


def _tokenize_quoted(line: str) -> list[str]:
    """Split line respecting double-quoted and single-quoted strings."""
    tokens = []
    current = []
    in_double = False
    in_single = False
    i = 0
    while i < len(line):
        c = line[i]
        if not in_double and not in_single:
            if c == '"':
                in_double = True
                i += 1
                continue
            if c == "'":
                in_single = True
                i += 1
                continue
            if c in " \t":
                if current:
                    tokens.append("".join(current))
                    current = []
                i += 1
                continue
            current.append(c)
            i += 1
            continue
        if in_double:
            if c == '"':
                in_double = False
                if current:
                    tokens.append("".join(current))
                    current = []
                i += 1
                continue
            if c == "\\" and i + 1 < len(line):
                i += 1
                current.append(line[i])
            else:
                current.append(c)
            i += 1
            continue
        if in_single:
            if c == "'":
                in_single = False
                if current:
                    tokens.append("".join(current))
                    current = []
                i += 1
                continue
            current.append(c)
            i += 1
            continue
    if current:
        tokens.append("".join(current))
    return tokens


def _resolve_index_ref(rest: str, recent_ids: list[str]) -> str:
    """If rest is #N, return recent_ids[N-1] if in range, else return rest as-is."""
    rest = rest.strip()
    if rest.startswith("#") and len(recent_ids) > 0:
        try:
            idx = int(rest[1:].strip())
            if 1 <= idx <= len(recent_ids):
                return recent_ids[idx - 1]
        except ValueError:
            pass
    return rest


def parse_line(
    line: str,
    *,
    recent_request_ids: list[str] | None = None,
) -> ParsedCommand:
    """
    Parse a single input line into command and rest.
    - Strips and normalizes whitespace.
    - Resolves aliases.
    - Supports quoted strings in rest.
    - If line is a single digit 0-9, treat as menu choice (is_menu_number=True, menu_index=N).
    - For unknown commands, set suggestion when applicable.
    """
    line = line.strip()
    if not line:
        return ParsedCommand(command="", rest="")

    recent_ids = recent_request_ids or []
    tokens = _tokenize_quoted(line)

    # Single digit -> menu number
    if len(tokens) == 1 and tokens[0].isdigit():
        n = int(tokens[0])
        if 0 <= n <= 9:
            return ParsedCommand(
                command="menu",
                rest="",
                is_menu_number=True,
                menu_index=n,
            )

    cmd_raw = tokens[0].lower()
    rest_tokens = tokens[1:]
    rest = " ".join(rest_tokens).strip() if rest_tokens else ""

    cmd = ALIASES.get(cmd_raw, cmd_raw)
    if cmd not in CANONICAL_COMMANDS and cmd != "menu":
        suggestion = None
        if cmd_raw == "tasks":
            suggestion = "Use 'status <task_id>' or 'dashboard' (2) to view requests."
        elif cmd_raw in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            pass  # already handled as menu above if single token
        return ParsedCommand(command=cmd_raw, rest=rest, suggestion=suggestion)

    # Resolve #N for rest when it's a task id argument
    if cmd in ("status", "watch", "events", "dashboard") and rest and recent_ids:
        rest = _resolve_index_ref(rest, recent_ids)

    return ParsedCommand(command=cmd, rest=rest)


def parse_for_submit(line: str) -> str:
    """
    Extract prompt from line for submit. Handles quoted wrap; if no quotes, returns line as-is after first word.
    """
    line = line.strip()
    tokens = _tokenize_quoted(line)
    if len(tokens) <= 1:
        return ""
    return " ".join(tokens[1:]).strip()
