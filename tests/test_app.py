from __future__ import annotations

from datetime import datetime, timezone

from bramer_briefing import create_app
from bramer_briefing.models import Article, Briefing, UserPreference, db
from bramer_briefing.scoring.ranker import score_article
from bramer_briefing.services.briefings import generate_briefing


def make_app():
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})


def test_dashboard_loads():
    app = make_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Bramer Briefing" in response.data


def test_scoring_prefers_breakthroughs():
    app = make_app()
    with app.app_context():
        article = Article(
            title="Major chemistry breakthrough announced",
            source="Test",
            url="https://example.com/a",
            summary="A new discovery improves classroom science.",
            publication_date=datetime.now(timezone.utc),
            category="Chemistry",
        )
        db.session.add(article)
        db.session.commit()
        assert score_article(article) > UserPreference.query.filter_by(category="Chemistry").first().weight


def test_generate_briefing_creates_items():
    app = make_app()
    with app.app_context():
        db.session.add(Article(title="NASA mission discovery", source="Test", url="https://example.com/nasa", summary="Space momentum", category="Space", relevance_score=50))
        db.session.commit()
        briefing = generate_briefing()
        assert isinstance(briefing, Briefing)
        assert len(briefing.items) == 1
        assert briefing.top_article.title == "NASA mission discovery"
