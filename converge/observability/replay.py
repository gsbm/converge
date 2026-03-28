import inspect
from pathlib import Path
from typing import Any

from converge.core.message import Message


class ReplayLog:
    """
    Manages the recording and playback of system events for debugging and analysis.
    """
    def __init__(self):
        self.events: list[Any] = []

    def record_inbound(self, message: Message, *, agent_id: str | None = None, transport: str | None = None) -> None:
        """
        Record an inbound message event.
        """
        self.events.append({
            "type": "message",
            "direction": "inbound",
            "agent_id": agent_id,
            "transport": transport,
            "timestamp": message.timestamp,
            "data": message.to_dict(),
        })

    def record_outbound(self, message: Message, *, agent_id: str | None = None, transport: str | None = None) -> None:
        """
        Record an outbound message event.
        """
        self.events.append({
            "type": "message",
            "direction": "outbound",
            "agent_id": agent_id,
            "transport": transport,
            "timestamp": message.timestamp,
            "data": message.to_dict(),
        })

    def record_message(self, message: Message) -> None:
        """
        Compatibility alias for outbound message recording.
        """
        self.record_outbound(message)

    def export(self, filepath: str) -> None:
        """
        Export the log to a file.
        """
        import json
        with Path(filepath).open("w") as f:
            json.dump(self.events, f, default=str)

    def load(self, filepath: str) -> None:
        """
        Load a log from a file.
        """
        import json
        with Path(filepath).open() as f:
            self.events = json.load(f)


class ReplayRunner:
    """
    Replays message events from ReplayLog into an inbox or callback.
    """

    def __init__(self, replay_log: ReplayLog):
        self.replay_log = replay_log

    async def replay(
        self,
        *,
        inbox=None,
        callback=None,
        direction: str | None = None,
        agent_id: str | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for event in self.replay_log.events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "message":
                continue
            if direction is not None and event.get("direction") != direction:
                continue
            if agent_id is not None and event.get("agent_id") != agent_id:
                continue
            ts = int(event.get("timestamp", 0))
            if start_ts is not None and ts < start_ts:
                continue
            if end_ts is not None and ts > end_ts:
                continue
            events.append(event)
        events.sort(key=lambda e: int(e.get("timestamp", 0)))
        if dry_run:
            return events
        from converge.core.message import Message

        for event in events:
            data = event.get("data", {})
            if not isinstance(data, dict):
                continue
            msg = Message.from_dict(data)
            if inbox is not None:
                await inbox.push(msg)
            elif callback is not None:
                out = callback(msg)
                if inspect.isawaitable(out):
                    await out
        return events
