# trackerZ type definitions
# Rev 0.1.0

from __future__ import annotations
from typing import Literal

# Entity classification hierarchy: project → task → subtask
EntityType = Literal["project", "task", "subtask"]

