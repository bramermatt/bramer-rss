from __future__ import annotations

import click
from flask import Flask, current_app

from bramer_briefing.feeds.reader import fetch_feeds
from bramer_briefing.models import Article, db
from bramer_briefing.scoring.ranker import rescore_articles
from bramer_briefing.services.briefings import generate_briefing


def register_cli(app: Flask) -> None:
    @app.cli.command("fetch-feeds")
    def fetch_feeds_command() -> None:
        """Download configured RSS feeds and store new articles."""
        count = fetch_feeds(current_app.config["FEEDS_CONFIG"])
        click.echo(f"Fetched {count} new articles.")

    @app.cli.command("refresh-articles")
    def refresh_articles_command() -> None:
        """Re-score articles after preference or scoring changes."""
        articles = Article.query.all()
        rescore_articles(articles)
        db.session.commit()
        click.echo(f"Refreshed {len(articles)} articles.")

    @app.cli.command("generate-briefing")
    def generate_briefing_command() -> None:
        """Generate a new five-minute briefing."""
        briefing = generate_briefing()
        click.echo(f"Generated briefing #{briefing.id}.")

    @app.cli.command("rebuild-db")
    def rebuild_db_command() -> None:
        """Drop and recreate the local SQLite database."""
        db.drop_all()
        db.create_all()
        from bramer_briefing.services.books import seed_default_books
        from bramer_briefing.services.preferences import seed_default_preferences

        seed_default_preferences()
        seed_default_books()
        click.echo("Database rebuilt.")
