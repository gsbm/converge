from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from converge.core.message import Message

if TYPE_CHECKING:
    from converge.network.identity_registry import IdentityRegistry


class Transport(ABC):
    """
    Abstract base class for transports.
    Transports are hot-swappable, stateless, and observable.
    """

    @abstractmethod
    async def send(self, message: Message) -> None:
        """Send a message."""
        pass

    @abstractmethod
    async def receive(self, timeout: float | None = None) -> Message:
        """
        Receive a message.
        If timeout is set, return within that many seconds or raise TimeoutError.
        """
        pass

    async def receive_verified(
        self,
        identity_registry: "IdentityRegistry",
        timeout: float | None = None,
    ) -> Message | None:
        """
        Receive a message and verify its signature.
        Returns the message if verified, or None if verification fails.
        If timeout is set, receive must complete within that time or TimeoutError is raised.
        Default implementation receives and verifies via Message.verify().
        """
        msg = await self.receive(timeout=timeout)
        pubkey = identity_registry.get(msg.sender)
        if pubkey and msg.verify(pubkey):
            return msg
        return None

    @abstractmethod
    async def start(self) -> None:
        """Start the transport."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport."""
        pass
