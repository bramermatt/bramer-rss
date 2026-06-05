"""RSS feed ingestion."""
from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from bramer_briefing.models import Article, db
from bramer_briefing.scoring.ranker import rescore_articles

LOGGER = logging.getLogger(__name__)


def load_feed_config(path: str | Path) -> dict[str, list[dict[str, str]]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    categories = data.get("categories", data)
    return categories or {}


def clean_summary(value: str | None) -> str:
    if not value:
        return "No summary available."
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(text.split())[:500]


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def parse_date(entry: dict) -> datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            try:
                return parsedate_to_datetime(value)
            except (TypeError, ValueError, IndexError, AttributeError):
                LOGGER.debug("Could not parse date %s", value)
    return None


def fetch_feeds(config_path: str | Path, timeout: int = 15) -> int:
    categories = load_feed_config(config_path)
    saved = 0
    for category, feeds in categories.items():
        for feed in feeds or []:
            feed_url = feed["url"] if isinstance(feed, dict) else str(feed)
            fallback_source = feed.get("name", category) if isinstance(feed, dict) else category
            try:
                response = requests.get(feed_url, timeout=timeout, headers={"User-Agent": "BramerBriefing/1.0"})
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
            except Exception as exc:  # network and parser failures should not stop the briefing
                LOGGER.warning("Feed failed: %s (%s)", feed_url, exc)
                continue

            if not parsed.entries:
                LOGGER.info("Feed was empty: %s", feed_url)
                continue

            source = parsed.feed.get("title") or fallback_source
            for entry in parsed.entries:
                if not entry.get("title") or not entry.get("link"):
                    continue
                url = canonical_url(entry.link)
                if Article.query.filter_by(url=url).first():
                    continue
                article = Article(
                    title=entry.title.strip(),
                    source=source,
                    url=url,
                    summary=clean_summary(entry.get("summary") or entry.get("description")),
                    publication_date=parse_date(entry),
                    category=category,
                )
                db.session.add(article)
                saved += 1
    db.session.flush()
    articles = Article.query.all()
    rescore_articles(articles)
    db.session.commit()
    return saved
