from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from bramer_briefing import generator
from bramer_briefing.models import Article, Book


def test_rank_articles_rewards_breakthroughs() -> None:
    articles = [
        Article("Celebrity rumor", "Example", "https://example.com/1", "Books", "Low information rumor.", None),
        Article("Major chemistry breakthrough", "Example", "https://example.com/2", "Science", "A discovery for classroom discussion.", datetime.now(timezone.utc)),
    ]

    ranked = generator.rank_articles(articles)

    assert ranked[0].title == "Major chemistry breakthrough"
    assert ranked[0].score > ranked[1].score


def test_choose_book_rotates_by_day() -> None:
    books = [
        Book("Knowing God", "J. I. Packer", "Theology", "Classic theology."),
        Book("1776", "David McCullough", "History", "American history."),
        Book("The Disappearing Spoon", "Sam Kean", "Science", "Chemistry history."),
        Book("The Fellowship of the Ring", "J. R. R. Tolkien", "Fantasy", "Fantasy classic."),
    ]

    selected = generator.choose_book(books, datetime(2026, 6, 5, tzinfo=timezone.utc))

    assert selected is not None
    assert selected.category in {"Theology", "History", "Science", "Fantasy"}


def test_build_site_writes_index(monkeypatch, tmp_path: Path) -> None:
    feeds_path = tmp_path / "feeds.yml"
    books_path = tmp_path / "books.yml"
    feeds_path.write_text("Science:\n  - name: Example\n    url: https://example.com/feed\n", encoding="utf-8")
    books_path.write_text("Science:\n  - title: Test Book\n    author: Test Author\n    note: Test note.\n", encoding="utf-8")
    sample_article = Article(
        "Major space discovery",
        "Example",
        "https://example.com/story",
        "Science",
        "A telescope mission demonstrates momentum and energy.",
        datetime.now(timezone.utc),
        42,
    )
    monkeypatch.setattr(generator, "collect_articles", lambda feeds: ([sample_article], []))

    index_path = generator.build_site(feeds_path, books_path, tmp_path / "site")

    html = index_path.read_text(encoding="utf-8")
    assert "Bramer Briefing" in html
    assert "Major space discovery" in html
    assert "Classroom Connections" in html


def test_entrypoint_is_static_generator() -> None:
    entrypoint = Path("main.py").read_text(encoding="utf-8")
    package_init = Path("bramer_briefing/__init__.py").read_text(encoding="utf-8")

    assert "from bramer_briefing.generator import main" in entrypoint
    assert "create_app" not in entrypoint
    assert "flask" not in entrypoint.lower()
    assert "flask" not in package_init.lower()

