"""Shared data structures for Bramer Briefing."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Feed:
    """A configured RSS or Atom feed."""

    category: str
    name: str
    url: str


@dataclass(slots=True)
class Article:
    """A normalized article from an RSS or Atom feed."""

    title: str
    source: str
    url: str
    category: str
    summary: str
    published: datetime | None
    score: float = 0.0


@dataclass(slots=True)
class Book:
    """A book available for the daily rotating recommendation."""

    title: str
    author: str
    category: str
    note: str


@dataclass(slots=True)
class Connection:
    """A classroom or ministry connection derived from a story."""

    title: str
    url: str
    explanation: str
    label: str
