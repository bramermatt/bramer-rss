"""Article relevance scoring for curated five-minute briefings."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from bramer_briefing.models import Article, UserPreference

POSITIVE_TERMS = {
    "breakthrough": 8,
    "discovery": 7,
    "major": 5,
    "first": 4,
    "new study": 4,
    "mission": 4,
    "launch": 4,
    "telescope": 4,
    "archaeology": 5,
    "ancient": 3,
    "release": 4,
    "model": 3,
    "classroom": 4,
    "teaching": 4,
    "church": 3,
    "ministry": 4,
    "president": 3,
    "history": 3,
}
NEGATIVE_TERMS = {
    "celebrity": -8,
    "you won't believe": -8,
    "shocking": -5,
    "sponsored": -6,
    "deal": -5,
    "sale": -5,
    "opinion": -3,
    "rumor": -4,
}

DEFAULT_WEIGHTS = {
    "Theology": 10,
    "Biblical Studies": 10,
    "Science": 10,
    "Physics": 10,
    "Chemistry": 10,
    "Education": 9,
    "History": 8,
    "AI": 8,
    "Technology": 6,
    "Books": 6,
    "Space": 9,
    "Church Leadership": 8,
}


def score_article(article: Article, duplicate_titles: Counter[str] | None = None) -> float:
    text = f"{article.title} {article.summary or ''}".lower()
    prefs = {p.category: p.weight for p in UserPreference.query.all()}
    score = float(prefs.get(article.category, DEFAULT_WEIGHTS.get(article.category, 5)))

    for term, weight in POSITIVE_TERMS.items():
        if term in text:
            score += weight
    for term, weight in NEGATIVE_TERMS.items():
        if term in text:
            score += weight

    if duplicate_titles:
        score += min(duplicate_titles.get(normalize_title(article.title), 0), 4) * 2

    if article.publication_date:
        now = datetime.now(timezone.utc)
        pub = article.publication_date.replace(tzinfo=timezone.utc) if article.publication_date.tzinfo is None else article.publication_date
        age_days = max((now - pub).days, 0)
        score += max(0, 7 - age_days)

    return max(score, 0.0)


def normalize_title(title: str) -> str:
    return " ".join(title.lower().split())[:120]


def rescore_articles(articles: list[Article]) -> None:
    counts = Counter(normalize_title(article.title) for article in articles)
    for article in articles:
        article.relevance_score = score_article(article, counts)
