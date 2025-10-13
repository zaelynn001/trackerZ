# Rev 0.5.1

"""Lightweight entities (Rev 0.5.1)"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    id: int | None
    name: str
    description: Optional[str] = None


@dataclass
class Task:
    id: int | None
    project_id: int
    name: str
    description: Optional[str] = None
    phase_id: int = 1


@dataclass
class Subtask:
    id: int | None
    task_id: int
    name: str
    description: Optional[str] = None
    phase_id: int = 1
