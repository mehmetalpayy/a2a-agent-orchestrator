"""Shared helpers and lightweight types."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass


class ParticipantRole(Enum):
    """Roles that a conversation participant may take."""

    ASSISTANT = "assistant"
    USER = "user"


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class ConversationMessage:
    """Internal representation of a single conversation message."""

    role: ParticipantRole | str
    content: list[Any] = Field(default_factory=list)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def text(self) -> str | None:
        """Return the primary text payload if present."""
        if not self.content:
            return None
        first = self.content[0]
        if isinstance(first, dict):
            if "text" in first:
                return first["text"]
            if "content" in first:
                return first["content"]
        if isinstance(first, str):
            return first
        return str(first)

    def to_dict(self) -> dict[str, Any]:
        """Convert the message to a JSON-serialisable dictionary."""
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "role": self.role.value if isinstance(self.role, Enum) else self.role,
            "content": self.content,
        }


TemplateVariables = dict[str, str | list[str]]
