"""Tool protocol and registry for agent tool execution."""

from typing import Any, Protocol


class Tool(Protocol):
    """
    Protocol for executable tools.
    Agents emit InvokeTool decisions; the executor looks up the tool by name and runs it.
    Optional: implement a ``schema`` property returning a JSON Schema dict for params
    (used for provider tool definitions and prompt injection).
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


def get_tool_schema(tool: Tool) -> dict[str, Any] | None:
    """Return the tool's param schema (JSON Schema) if defined, else None."""
    return getattr(tool, "schema", None)


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

    def to_provider_tools(self) -> list[dict[str, Any]]:
        """
        Return tool definitions in OpenAI-compatible format for provider APIs.
        Each tool has type "function", "function.name", "function.description", "function.parameters" (JSON Schema).
        Tools without a schema get a generic parameters schema accepting an object.
        """
        result = []
        for tool in self._tools.values():
            schema = get_tool_schema(tool)
            if schema is None:
                params_schema = {"type": "object", "properties": {}, "additionalProperties": True}
            elif schema.get("type") == "object":
                params_schema = schema
            else:
                params_schema = {"type": "object", "properties": schema if isinstance(schema, dict) else {}, "required": []}
            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": getattr(tool, "description", None) or f"Tool: {tool.name}",
                    "parameters": params_schema,
                },
            })
        return result
