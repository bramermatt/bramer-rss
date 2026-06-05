from __future__ import annotations

from collections import defaultdict

from bramer_briefing.models import Article, Briefing, BriefingItem, db
from bramer_briefing.services.books import book_of_the_day
from bramer_briefing.services.connections import classroom_connections, ministry_connections

PRIMARY_SECTIONS = ["Science", "Space", "AI", "Education", "Theology", "History", "Books"]


def generate_briefing(limit: int = 15) -> Briefing:
    articles = Article.query.order_by(Article.relevance_score.desc(), Article.publication_date.desc().nullslast()).limit(limit).all()
    briefing = Briefing(estimated_read_time=5, top_article=articles[0] if articles else None)
    db.session.add(briefing)
    db.session.flush()
    for position, article in enumerate(articles, start=1):
        section = article.category if article.category in PRIMARY_SECTIONS else "Top Stories"
        db.session.add(BriefingItem(briefing_id=briefing.id, article_id=article.id, section=section, position=position))
    db.session.commit()
    return briefing


def latest_briefing() -> Briefing | None:
    return Briefing.query.order_by(Briefing.generated_at.desc()).first()


def briefing_context(briefing: Briefing | None = None) -> dict:
    briefing = briefing or latest_briefing()
    if briefing is None:
        briefing = generate_briefing()
    articles = [item.article for item in briefing.items]
    grouped: dict[str, list[Article]] = defaultdict(list)
    for item in briefing.items:
        grouped[item.section].append(item.article)
    return {
        "briefing": briefing,
        "top_story": briefing.top_article,
        "grouped": grouped,
        "classroom_connections": classroom_connections(articles),
        "ministry_connections": ministry_connections(articles),
        "book": book_of_the_day(),
    }
