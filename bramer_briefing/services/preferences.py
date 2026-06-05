from __future__ import annotations

from bramer_briefing.models import UserPreference, db
from bramer_briefing.scoring.ranker import DEFAULT_WEIGHTS


def seed_default_preferences() -> None:
    for category, weight in DEFAULT_WEIGHTS.items():
        if not UserPreference.query.filter_by(category=category).first():
            db.session.add(UserPreference(category=category, weight=weight))
    db.session.commit()
