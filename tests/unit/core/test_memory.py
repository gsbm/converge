"""Tests for converge.core.memory."""


from converge.core.memory import ShortTermMemory


def test_short_term_memory_append_and_get():
    mem = ShortTermMemory(max_messages=5)
    mem.append("user", "hello")
    mem.append("assistant", "hi")
    msgs = mem.get_messages()
    assert len(msgs) == 2
    assert msgs[0] == {"role": "user", "content": "hello"}
    assert msgs[1] == {"role": "assistant", "content": "hi"}


def test_short_term_memory_trim():
    mem = ShortTermMemory(max_messages=3)
    for i in range(5):
        mem.append("user", f"m{i}")
    msgs = mem.get_messages()
    assert len(msgs) == 3
    assert msgs[0]["content"] == "m2"
    assert msgs[-1]["content"] == "m4"


def test_short_term_memory_clear():
    mem = ShortTermMemory(max_messages=5)
    mem.append("user", "x")
    mem.clear()
    assert mem.get_messages() == []
