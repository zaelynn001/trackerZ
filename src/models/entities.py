# Rev 0.6.5
"""Lightweight entities aligned with schema Rev 0.6.5 (phase_id + priority_id)"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    id: int | None
    name: str
    description: Optional[str] = None
    phase_id: int = 1          # new: NOT NULL in DB
    priority_id: int = 2       # new: NOT NULL in DB (default Medium)


@dataclass
class Task:
    id: int | None
    project_id: int
    name: str
    description: Optional[str] = None
    phase_id: int = 1          # existing
    priority_id: int = 2       # new: NOT NULL in DB (default Medium)


@dataclass
class Subtask:
    id: int | None
    task_id: int
    name: str
    description: Optional[str] = None
    phase_id: int = 1          # existing
    priority_id: int = 2       # new: NOT NULL in DB (default Medium)
