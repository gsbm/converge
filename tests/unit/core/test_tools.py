"""Tests for converge.core.tools."""

from converge.core.tools import ToolRegistry, get_tool_schema


class _EchoTool:
    @property
    def name(self) -> str:
        return "echo"

    def run(self, params: dict) -> str:
        return str(params.get("text", ""))


class _ToolWithSchema:
    @property
    def name(self) -> str:
        return "search"

    @property
    def schema(self) -> dict:
        return {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}

    def run(self, params: dict):
        return params.get("query", "")


def test_tool_registry_register_get():
    registry = ToolRegistry()
    tool = _EchoTool()
    registry.register(tool)
    assert registry.get("echo") is tool
    assert registry.get("missing") is None


def test_tool_registry_list_names():
    registry = ToolRegistry()
    registry.register(_EchoTool())
    class OtherTool:
        @property
        def name(self) -> str:
            return "other"
        def run(self, params: dict):
            return None
    registry.register(OtherTool())
    names = registry.list_names()
    assert set(names) == {"echo", "other"}


def test_tool_run():
    tool = _EchoTool()
    assert tool.run({"text": "hello"}) == "hello"
    assert tool.run({}) == ""


def test_get_tool_schema_none():
    assert get_tool_schema(_EchoTool()) is None


def test_get_tool_schema_present():
    assert get_tool_schema(_ToolWithSchema()) == {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}


def test_tool_registry_to_provider_tools():
    registry = ToolRegistry()
    registry.register(_EchoTool())
    registry.register(_ToolWithSchema())
    tools = registry.to_provider_tools()
    assert len(tools) == 2
    names = {t["function"]["name"] for t in tools}
    assert names == {"echo", "search"}
    echo_def = next(t for t in tools if t["function"]["name"] == "echo")
    assert echo_def["function"]["parameters"]["type"] == "object"
    search_def = next(t for t in tools if t["function"]["name"] == "search")
    assert search_def["function"]["parameters"]["properties"]["query"]["type"] == "string"
    assert "query" in search_def["function"]["parameters"]["required"]
