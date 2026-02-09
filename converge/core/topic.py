from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Topic:
    """
    Topic for routing and semantic filtering.
    """
    namespace: str
    attributes: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"

    def __str__(self) -> str:
        attrs = ",".join(f"{k}={v}" for k, v in sorted(self.attributes.items()))
        return f"{self.namespace}[{attrs}]v{self.version}"

    def to_dict(self) -> dict[str, Any]:
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Topic":
        return cls(**data)
