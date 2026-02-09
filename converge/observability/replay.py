from pathlib import Path
from typing import Any

from converge.core.message import Message


class ReplayLog:
    """
    Manages the recording and playback of system events for debugging and analysis.
    """
    def __init__(self):
        self.events: list[Any] = []

    def record_message(self, message: Message) -> None:
        """
        Record a message dispatch event.
        """
        self.events.append({
            "type": "message",
            "timestamp": message.timestamp,
            "data": message.to_dict(),
        })

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
