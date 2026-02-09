import asyncio


class Scheduler:
    """
    Event-driven scheduler for the agent runtime.
    Replaces busy-wait polling with asyncio.Event signaling.
    """
    def __init__(self):
        self._wake_event = asyncio.Event()

    def notify(self) -> None:
        """
        Notify the scheduler that new work is available.
        This will wake up the loop if it is waiting.
        """
        self._wake_event.set()

    async def wait_for_work(self, timeout: float | None = None) -> bool:
        """
        Wait until new work is available or timeout occurs.

        Args:
            timeout (float): Max time to wait in seconds.

        Returns:
            bool: True if woken by event, False if timeout.
        """
        try:
            await asyncio.wait_for(self._wake_event.wait(), timeout=timeout)
            # Clear event immediately so we wait again next time unless notified again
            self._wake_event.clear()
            return True
        except TimeoutError:
            return False
