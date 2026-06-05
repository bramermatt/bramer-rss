#!/usr/bin/env python3
"""Bramer Briefing: a simple static HTML briefing generator.

This script fetches RSS/Atom feeds, scores recent articles, and writes one
responsive, mobile-friendly HTML page. It intentionally has no web server,
database, framework, or required third-party dependencies.
"""
from __future__ import annotations

import argparse
import html
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

APP_NAME = "Bramer Briefing"
DEFAULT_OUTPUT = Path("output/bramer-briefing.html")
DEFAULT_TIMEOUT_SECONDS = 15
MAX_ARTICLES_PER_FEED = 12
BRIEFING_STORY_COUNT = 15

DEFAULT_FEEDS: dict[str, list[str]] = {
    "Science": [
        "https://www.sciencedaily.com/rss/all.xml",
        "https://phys.org/rss-feed/",
    ],
    "Physics": ["https://physicsworld.com/feed/"],
    "Chemistry": ["https://cen.acs.org/rss/latest.xml"],
    "Space": [
        "https://www.nasa.gov/news-release/feed/",
        "https://www.planetary.org/planetary-radio/show.rss",
    ],
    "AI": [
        "https://openai.com/news/rss.xml",
        "https://www.anthropic.com/news/rss.xml",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
    ],
    "Technology": ["https://feeds.arstechnica.com/arstechnica/index"],
    "Education": [
        "https://www.edutopia.org/rss.xml",
        "https://www.edweek.org/feeds/feed-education-week.rss",
    ],
    "Theology": [
        "https://www.thegospelcoalition.org/feed/",
        "https://www.9marks.org/feed/",
        "https://www.ligonier.org/learn/rss",
    ],
    "Biblical Studies": [
        "https://www.logos.com/grow/feed/",
        "https://www.biblicalarchaeology.org/feed/",
    ],
    "Church Leadership": ["https://churchleaders.com/feed"],
    "History": ["https://allthingsliberty.com/feed/"],
    "Books": ["https://lithub.com/feed/"],
}

CATEGORY_WEIGHTS: dict[str, int] = {
    "Theology": 10,
    "Biblical Studies": 10,
    "Science": 10,
    "Physics": 10,
    "Chemistry": 10,
    "Space": 9,
    "Education": 9,
    "History": 8,
    "AI": 8,
    "Church Leadership": 8,
    "Technology": 6,
    "Books": 6,
}

POSITIVE_TERMS: dict[str, int] = {
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

NEGATIVE_TERMS: dict[str, int] = {
    "celebrity": -8,
    "you won't believe": -8,
    "shocking": -5,
    "sponsored": -6,
    "deal": -5,
    "sale": -5,
    "opinion": -3,
    "rumor": -4,
}

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class Article:
    """A normalized article extracted from an RSS or Atom feed."""

    title: str
    url: str
    source: str
    category: str
    summary: str
    published: datetime | None
    score: float = 0.0


@dataclass(slots=True)
class FeedResult:
    """Result of fetching and parsing one feed URL."""

    url: str
    category: str
    article_count: int
    error: str | None = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a static Bramer Briefing HTML page.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"HTML output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--feeds", type=Path, help="Optional simple YAML feed file. If omitted, built-in feeds are used.")
    parser.add_argument("--max-stories", type=int, default=BRIEFING_STORY_COUNT, help="Maximum stories in the briefing.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Network timeout in seconds per feed.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed fetch logging.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    feeds = load_feeds(args.feeds) if args.feeds else DEFAULT_FEEDS
    articles, results = collect_articles(feeds, timeout=args.timeout)
    ranked = rank_articles(articles)[: max(args.max_stories, 1)]
    html_page = render_html(ranked, results, generated_at=datetime.now(timezone.utc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_page, encoding="utf-8")
    print(f"Generated {args.output} with {len(ranked)} stories from {len(articles)} parsed articles.")
    return 0


def load_feeds(path: Path) -> dict[str, list[str]]:
    """Load a tiny YAML-like category-to-feed-list file without dependencies.

    Expected format:

        Science:
          - https://example.com/rss.xml
        AI:
          - https://example.com/feed.xml
    """
    feeds: dict[str, list[str]] = {}
    current_category: str | None = None
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith((" ", "\t")) and stripped.endswith(":"):
            current_category = stripped[:-1].strip()
            feeds.setdefault(current_category, [])
            continue
        if stripped.startswith("-") and current_category:
            url = stripped[1:].strip()
            if url:
                feeds[current_category].append(url)
            continue
        raise ValueError(f"Unsupported feed config syntax at {path}:{line_number}: {raw_line}")
    return {category: urls for category, urls in feeds.items() if urls}


def collect_articles(feeds: dict[str, list[str]], timeout: int) -> tuple[list[Article], list[FeedResult]]:
    articles: list[Article] = []
    results: list[FeedResult] = []
    seen_keys: set[str] = set()

    for category, urls in feeds.items():
        for feed_url in urls:
            try:
                body = fetch(feed_url, timeout=timeout)
                parsed = parse_feed(body, feed_url=feed_url, category=category)
                added = 0
                for article in parsed[:MAX_ARTICLES_PER_FEED]:
                    key = dedupe_key(article)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    articles.append(article)
                    added += 1
                results.append(FeedResult(feed_url, category, added))
            except (HTTPError, URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
                logging.warning("Skipping feed %s: %s", feed_url, exc)
                results.append(FeedResult(feed_url, category, 0, str(exc)))
    return articles, results


def fetch(url: str, timeout: int) -> bytes:
    request = Request(url, headers={"User-Agent": "BramerBriefingStatic/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_feed(body: bytes, feed_url: str, category: str) -> list[Article]:
    root = ET.fromstring(body)
    source = first_text(root, ["channel/title", "{http://www.w3.org/2005/Atom}title"]) or hostname(feed_url)
    items = root.findall(".//item") or root.findall("{http://www.w3.org/2005/Atom}entry")
    articles = [parse_item(item, source=source, category=category) for item in items]
    return [article for article in articles if article and article.title and article.url]


def parse_item(item: ET.Element, source: str, category: str) -> Article | None:
    atom = "{http://www.w3.org/2005/Atom}"
    title = clean_text(first_text(item, ["title", f"{atom}title"]))
    url = first_text(item, ["link", "guid"])
    atom_link = item.find(f"{atom}link")
    if atom_link is not None:
        url = atom_link.attrib.get("href", url)
    if not title or not url:
        return None
    summary = clean_text(
        first_text(
            item,
            [
                "description",
                "summary",
                "{http://purl.org/rss/1.0/modules/content/}encoded",
                f"{atom}summary",
                f"{atom}content",
            ],
        )
    )
    published = parse_date(first_text(item, ["pubDate", "published", "updated", f"{atom}published", f"{atom}updated"]))
    return Article(title=title, url=canonical_url(url), source=clean_text(source), category=category, summary=summary, published=published)


def first_text(element: ET.Element, paths: Iterable[str]) -> str:
    for path in paths:
        found = element.find(path)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = TAG_RE.sub(" ", html.unescape(value))
    return WHITESPACE_RE.sub(" ", without_tags).strip()


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError, AttributeError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def hostname(url: str) -> str:
    return urlsplit(url).netloc.removeprefix("www.") or "Unknown source"


def dedupe_key(article: Article) -> str:
    return article.url or WHITESPACE_RE.sub(" ", article.title.lower())[:120]


def rank_articles(articles: list[Article]) -> list[Article]:
    now = datetime.now(timezone.utc)
    title_counts: dict[str, int] = defaultdict(int)
    for article in articles:
        title_counts[WHITESPACE_RE.sub(" ", article.title.lower())[:90]] += 1

    for article in articles:
        text = f"{article.title} {article.summary}".lower()
        score = float(CATEGORY_WEIGHTS.get(article.category, 5))
        for term, weight in POSITIVE_TERMS.items():
            if term in text:
                score += weight
        for term, weight in NEGATIVE_TERMS.items():
            if term in text:
                score += weight
        if article.published:
            published = article.published if article.published.tzinfo else article.published.replace(tzinfo=timezone.utc)
            age_days = max((now - published).days, 0)
            score += max(0, 7 - age_days)
        score += min(title_counts[WHITESPACE_RE.sub(" ", article.title.lower())[:90]], 4) * 2
        article.score = max(score, 0.0)

    return sorted(articles, key=lambda article: (article.score, article.published or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)


def render_html(articles: list[Article], results: list[FeedResult], generated_at: datetime) -> str:
    grouped: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        grouped[article.category].append(article)

    top_story = articles[0] if articles else None
    failures = [result for result in results if result.error]
    successful_feeds = sum(1 for result in results if not result.error)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{APP_NAME}</title>
  <style>{css()}</style>
</head>
<body>
  <header class="masthead">
    <p class="eyebrow">Personal five-minute briefing</p>
    <h1>{APP_NAME}</h1>
    <p class="dek">If you only have five minutes today, here is what is most worth knowing.</p>
    <p class="meta">Generated {escape(generated_at.strftime('%B %d, %Y at %H:%M UTC'))} · {len(articles)} curated stories · {successful_feeds} feeds read</p>
  </header>
  <main>
    {render_top_story(top_story)}
    <nav class="category-nav">{''.join(f'<a href="#{slug(category)}">{escape(category)}</a>' for category in grouped)}</nav>
    {''.join(render_category(category, items) for category, items in grouped.items())}
    {render_connections(articles)}
    {render_feed_status(failures)}
  </main>
</body>
</html>
"""


def render_top_story(article: Article | None) -> str:
    if not article:
        return "<section class='empty'><h2>No stories found</h2><p>Try again later or add working feeds.</p></section>"
    return f"""<section class="top-story">
  <p class="eyebrow">Top Story</p>
  {render_article(article, featured=True)}
</section>"""


def render_category(category: str, articles: list[Article]) -> str:
    cards = "".join(render_article(article) for article in articles)
    return f"<section class='category' id='{slug(category)}'><h2>{escape(category)}</h2><div class='cards'>{cards}</div></section>"


def render_article(article: Article, featured: bool = False) -> str:
    date = article.published.strftime("%b %d, %Y") if article.published else "Recent"
    summary = article.summary or "No summary was available from the feed."
    summary = trim_sentence(summary, 220 if featured else 170)
    return f"""<article class="card{' featured' if featured else ''}">
  <div class="article-meta"><span>{escape(article.source)}</span><span>{escape(date)}</span><span>Score {article.score:.1f}</span></div>
  <h3><a href="{escape(article.url)}">{escape(article.title)}</a></h3>
  <p>{escape(summary)}</p>
</article>"""


def render_connections(articles: list[Article]) -> str:
    classroom = [article for article in articles if any(term in f"{article.title} {article.summary} {article.category}".lower() for term in ["physics", "chemistry", "space", "energy", "matter", "motion", "science", "telescope", "orbit"])]
    ministry = [article for article in articles if article.category in {"Theology", "Biblical Studies", "Church Leadership"} or any(term in f"{article.title} {article.summary}".lower() for term in ["bible", "church", "theology", "ministry", "archaeology"])]
    return f"""<section class="connections">
  <div><h2>Classroom Connections</h2>{render_connection_list(classroom[:4], 'Connect this story to ICP, Physical Science, Chemistry, or Physics discussion.')}</div>
  <div><h2>Faith & Ministry Connections</h2>{render_connection_list(ministry[:4], 'Useful for Bible teaching, theology, church leadership, or cultural engagement.')}</div>
</section>"""


def render_connection_list(articles: list[Article], note: str) -> str:
    if not articles:
        return "<p class='muted'>No strong matches in today’s feeds.</p>"
    return "".join(f"<article class='mini'><a href='{escape(article.url)}'>{escape(article.title)}</a><p>{escape(note)}</p></article>" for article in articles)


def render_feed_status(failures: list[FeedResult]) -> str:
    if not failures:
        return "<section class='feed-status'><h2>Feed Status</h2><p>All fetched feeds parsed without reported errors.</p></section>"
    items = "".join(f"<li><strong>{escape(result.category)}</strong>: {escape(result.url)} — {escape(result.error or '')}</li>" for result in failures)
    return f"<section class='feed-status'><h2>Feed Status</h2><p>Some feeds failed; the briefing was generated from the remaining feeds.</p><ul>{items}</ul></section>"


def trim_sentence(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    trimmed = text[:limit].rsplit(" ", 1)[0].rstrip(".,;: ")
    return f"{trimmed}…"


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def css() -> str:
    return """
:root{color-scheme:light dark;--bg:#f6f1e8;--paper:#fffaf0;--ink:#18212b;--muted:#65717e;--accent:#8f2d21;--line:#e2d3bd;--shadow:0 16px 40px rgba(24,33,43,.10)}
@media(prefers-color-scheme:dark){:root{--bg:#101419;--paper:#1b2028;--ink:#f5efe5;--muted:#aab3bf;--accent:#f0a45d;--line:#303846;--shadow:0 16px 40px rgba(0,0,0,.35)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Georgia,'Times New Roman',serif;line-height:1.6}a{color:inherit}.masthead{padding:clamp(2rem,7vw,5rem) 5vw;text-align:center;background:linear-gradient(135deg,var(--paper),color-mix(in srgb,var(--accent) 12%,var(--paper)));border-bottom:1px solid var(--line)}h1{font-size:clamp(2.6rem,11vw,6rem);line-height:.95;margin:.1em 0;letter-spacing:-.05em}.dek{max-width:760px;margin:0 auto 1rem;color:var(--muted);font-size:clamp(1.05rem,3vw,1.35rem)}.eyebrow,.meta,.article-meta{font-family:system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;font-weight:800;font-size:.75rem;color:var(--accent)}main{width:min(1120px,92vw);margin:0 auto;padding:1.5rem 0 4rem}.top-story,.category,.connections>div,.feed-status,.empty{background:var(--paper);border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);padding:clamp(1rem,3vw,1.5rem);margin:1rem 0}.category-nav{display:flex;gap:.6rem;overflow:auto;padding:.5rem 0 1rem;position:sticky;top:0;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px)}.category-nav a{white-space:nowrap;text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:.55rem .8rem;background:var(--paper);font-family:system-ui,sans-serif;color:var(--muted)}h2{font-size:clamp(1.5rem,5vw,2.2rem);border-bottom:3px solid var(--accent);padding-bottom:.25rem;margin-top:0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}.card{border-top:1px solid var(--line);padding:1rem 0}.cards .card{border:1px solid var(--line);border-radius:18px;padding:1rem;background:color-mix(in srgb,var(--paper) 88%,var(--bg))}.card.featured h3{font-size:clamp(1.7rem,5vw,3rem)}.card h3{font-size:1.25rem;line-height:1.15;margin:.5rem 0}.card p,.muted,.mini p,.feed-status{color:var(--muted)}.article-meta{display:flex;flex-wrap:wrap;gap:.8rem}.connections{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}.mini{border-top:1px solid var(--line);padding:.9rem 0}.mini a{font-weight:800}ul{padding-left:1.2rem}@media(max-width:620px){main{width:94vw}.category-nav{margin-left:-3vw;margin-right:-3vw;padding-left:3vw}.cards{grid-template-columns:1fr}.top-story,.category,.connections>div,.feed-status,.empty{border-radius:18px}}
""".strip()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
