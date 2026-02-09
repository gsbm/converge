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
    async def receive(self) -> Message:
        """Receive a message."""
        pass

    async def receive_verified(
        self,
        identity_registry: "IdentityRegistry",
    ) -> Message | None:
        """
        Receive a message and verify its signature.
        Returns the message if verified, or None if verification fails.
        Default implementation receives and verifies via Message.verify().
        """
        msg = await self.receive()
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
