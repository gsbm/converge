"""Tests for converge.core.tools."""

from converge.core.tools import ToolRegistry


class _EchoTool:
    @property
    def name(self) -> str:
        return "echo"

    def run(self, params: dict) -> str:
        return str(params.get("text", ""))


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
