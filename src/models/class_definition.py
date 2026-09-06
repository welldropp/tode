"""
models/class_definition.py
────────────────────────────
Data model for an annotation class (name, id, colour).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


def _random_hex_color() -> str:
    return f"#{random.randint(0, 0xFFFFFF):06x}"  # noqa: S311  # nosec B311


@dataclass
class ClassDefinition:
    """Represents a single annotation class."""

    name:  str
    id:    int
    color: str = field(default_factory=_random_hex_color)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Class name must not be empty.")
        if self.id < 0:
            raise ValueError("Class id must be non-negative.")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color}

    @classmethod
    def from_dict(cls, data: dict) -> ClassDefinition:
        return cls(name=data["name"], id=data["id"], color=data.get("color", _random_hex_color()))
