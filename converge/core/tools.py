"""Tool protocol and registry for agent tool execution."""

from typing import Any, Protocol


class Tool(Protocol):
    """
    Protocol for executable tools.
    Agents emit InvokeTool decisions; the executor looks up the tool by name and runs it.
    """

    @property
    def name(self) -> str:
        """Tool name used in InvokeTool.tool_name."""
        ...

    def run(self, params: dict[str, Any]) -> Any:
        """
        Run the tool with the given parameters.

        Args:
            params: Key-value arguments for the tool.

        Returns:
            Result of the tool (e.g. str, dict, or serializable value).
        """
        ...


class ToolRegistry:
    """
    Registry mapping tool names to Tool instances.
    Used by StandardExecutor to execute InvokeTool decisions.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by its name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name, or None if not registered."""
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        """Return all registered tool names."""
        return list(self._tools.keys())
