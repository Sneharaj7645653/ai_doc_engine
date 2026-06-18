"""Simple data models for change detection and documentation staleness."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChangedUnit:
    """Represents one function-level change detected from a Git patch."""

    name: str
    change_type: str
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    old_return_type: Optional[str] = None
    new_return_type: Optional[str] = None
    reason: str = ""


@dataclass
class StalenessFlag:
    """Represents the final documentation staleness result for a file."""

    filename: str
    severity: str
    reason: str
    changed_units: List[ChangedUnit] = field(default_factory=list)
