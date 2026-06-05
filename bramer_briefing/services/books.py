from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from bramer_briefing.models import BookRecommendation, db

BOOK_CYCLE = ["Theology", "History", "Science", "Fantasy"]


def seed_default_books() -> None:
    if BookRecommendation.query.first():
        return
    path = Path(__file__).resolve().parents[1] / "config" / "books.yaml"
    with path.open("r", encoding="utf-8") as handle:
        for item in yaml.safe_load(handle) or []:
            db.session.add(BookRecommendation(**item))
    db.session.commit()


def book_of_the_day() -> BookRecommendation | None:
    books = BookRecommendation.query.order_by(BookRecommendation.last_recommended_at.asc().nullsfirst()).all()
    if not books:
        return None
    today_slot = datetime.now(timezone.utc).toordinal() % len(BOOK_CYCLE)
    preferred = BOOK_CYCLE[today_slot]
    book = next((b for b in books if b.category == preferred), books[0])
    book.last_recommended_at = datetime.now(timezone.utc)
    db.session.commit()
    return book
