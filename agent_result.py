"""Format commun de résultat des agents."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AgentResult:
    agent_name: str
    status: str
    summary: str
    issues: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        """Retourne le résultat sous une forme facilement affichable."""
        return asdict(self)
