"""Generate the Bramer Briefing static website using only the Python standard library."""
from __future__ import annotations

import argparse
import hashlib
import html
import logging
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from bramer_briefing.models import Article, Book, Connection, Feed

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEEDS = ROOT / "config" / "feeds.yml"
DEFAULT_BOOKS = ROOT / "config" / "books.yml"
DEFAULT_TEMPLATE = ROOT / "templates" / "index.html"
DEFAULT_STATIC_DIR = ROOT / "static"
DEFAULT_OUTPUT_DIR = ROOT / "public"
SECTION_ORDER = ["Science", "Space", "AI", "Education", "Theology", "History", "Books"]
BRIEFING_LIMIT = 15
PER_FEED_LIMIT = 12
REQUEST_TIMEOUT = 20

SECTION_ALIASES = {
    "Biblical Studies": "Theology",
    "Church Leadership": "Theology",
    "Technology": "AI",
    "Physics": "Science",
    "Chemistry": "Science",
}
CATEGORY_WEIGHTS = {
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
CLASSROOM_TERMS = {
    "Physics": ["physics", "force", "motion", "momentum", "orbit", "gravity", "energy", "quantum", "telescope"],
    "Chemistry": ["chemistry", "chemical", "molecule", "reaction", "element", "compound", "material"],
    "Physical Science": ["energy", "matter", "waves", "electricity", "magnet", "force", "motion"],
    "ICP": ["science", "experiment", "climate", "space", "matter", "energy", "engineering"],
}
MINISTRY_TERMS = ["bible", "theology", "church", "ministry", "pastor", "discipleship", "culture", "archaeology", "scripture"]
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Bramer Briefing GitHub Pages site.")
    parser.add_argument("--feeds", type=Path, default=DEFAULT_FEEDS, help="Path to RSS feed YAML configuration.")
    parser.add_argument("--books", type=Path, default=DEFAULT_BOOKS, help="Path to Book of the Day YAML configuration.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for the static site.")
    parser.add_argument("--limit", type=int, default=BRIEFING_LIMIT, help="Maximum number of stories in the briefing.")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed logging.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    build_site(feeds_path=args.feeds, books_path=args.books, output_dir=args.output, limit=args.limit)


def build_site(feeds_path: Path, books_path: Path, output_dir: Path, limit: int = BRIEFING_LIMIT) -> Path:
    """Build the static website and return the generated index path."""
    generated_at = datetime.now(timezone.utc)
    feeds = load_feeds(feeds_path)
    articles, feed_errors = collect_articles(feeds)
    ranked = rank_articles(articles)[:limit]
    sections = group_for_sections(ranked[1:])
    html_page = render_page(
        generated_at=generated_at,
        top_story=ranked[0] if ranked else None,
        sections=sections,
        classroom=classroom_connections(ranked),
        ministry=ministry_connections(ranked),
        book=choose_book(load_books(books_path), generated_at),
        article_count=len(ranked),
        feed_count=len(feeds),
        feed_errors=feed_errors,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    static_output = output_dir / "static"
    if static_output.exists():
        shutil.rmtree(static_output)
    shutil.copytree(DEFAULT_STATIC_DIR, static_output)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    index_path = output_dir / "index.html"
    index_path.write_text(html_page, encoding="utf-8")
    LOGGER.info("Generated %s with %d curated stories.", index_path, len(ranked))
    return index_path


def load_feeds(path: Path) -> list[Feed]:
    """Read the simple YAML feed configuration."""
    records = parse_simple_yaml(path)
    return [Feed(category=category, name=str(item["name"]), url=str(item["url"])) for category, items in records.items() for item in items]


def load_books(path: Path) -> list[Book]:
    """Read the simple YAML Book of the Day configuration."""
    records = parse_simple_yaml(path)
    return [Book(category=category, title=str(item["title"]), author=str(item["author"]), note=str(item["note"])) for category, items in records.items() for item in items]


def parse_simple_yaml(path: Path) -> dict[str, list[dict[str, str]]]:
    """Parse the small category/list-of-maps YAML shape used by this project.

    This deliberately supports only the configuration shape in config/*.yml so
    the project can run in GitHub Actions without external dependencies.
    """
    data: dict[str, list[dict[str, str]]] = {}
    category: str | None = None
    current: dict[str, str] | None = None
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            category = stripped[:-1]
            data.setdefault(category, [])
            current = None
            continue
        if category is None:
            raise ValueError(f"Expected category at {path}:{line_number}")
        if stripped.startswith("- "):
            current = {}
            data[category].append(current)
            remainder = stripped[2:]
            if remainder:
                key, value = split_yaml_pair(remainder, path, line_number)
                current[key] = value
            continue
        if current is not None and ":" in stripped:
            key, value = split_yaml_pair(stripped, path, line_number)
            current[key] = value
            continue
        raise ValueError(f"Unsupported YAML syntax at {path}:{line_number}: {raw_line}")
    return data


def split_yaml_pair(text: str, path: Path, line_number: int) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"Expected key/value pair at {path}:{line_number}")
    key, value = text.split(":", 1)
    return key.strip(), value.strip().strip('"\'')


def collect_articles(feeds: list[Feed]) -> tuple[list[Article], list[str]]:
    """Download and parse configured RSS/Atom feeds."""
    articles: list[Article] = []
    errors: list[str] = []
    seen_urls: set[str] = set()
    for feed in feeds:
        try:
            body = fetch(feed.url)
            parsed = parse_feed(body, feed)
        except (HTTPError, URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            message = f"{feed.name}: {exc}"
            LOGGER.warning(message)
            errors.append(message)
            continue
        for article in parsed[:PER_FEED_LIMIT]:
            if article.url in seen_urls:
                continue
            seen_urls.add(article.url)
            articles.append(article)
    return articles, errors


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "BramerBriefing/1.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def parse_feed(body: bytes, feed: Feed) -> list[Article]:
    root = ET.fromstring(body)
    source = first_text(root, ["channel/title", "{http://www.w3.org/2005/Atom}title"]) or feed.name
    items = root.findall(".//item") or root.findall("{http://www.w3.org/2005/Atom}entry")
    articles = [article_from_item(item, feed, source) for item in items]
    return [article for article in articles if article is not None]


def article_from_item(item: ET.Element, feed: Feed, source: str) -> Article | None:
    atom = "{http://www.w3.org/2005/Atom}"
    title = clean_text(first_text(item, ["title", f"{atom}title"]))
    url = first_text(item, ["link", "guid"])
    atom_link = item.find(f"{atom}link")
    if atom_link is not None:
        url = atom_link.attrib.get("href", url)
    url = canonical_url(url)
    if not title or not url:
        return None
    summary = one_sentence(clean_text(first_text(item, ["description", "summary", "{http://purl.org/rss/1.0/modules/content/}encoded", f"{atom}summary", f"{atom}content"])))
    return Article(title=title, source=clean_text(source), url=url, category=feed.category, summary=summary or "No summary provided by the feed.", published=parse_date(first_text(item, ["pubDate", "published", "updated", f"{atom}published", f"{atom}updated"])))


def first_text(element: ET.Element, paths: Iterable[str]) -> str:
    for path in paths:
        found = element.find(path)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def parse_date(value: str) -> datetime | None:
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


def rank_articles(articles: list[Article]) -> list[Article]:
    now = datetime.now(timezone.utc)
    title_counts: dict[str, int] = defaultdict(int)
    for article in articles:
        title_counts[normalized_title(article.title)] += 1
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
            age_days = max((now - article.published.astimezone(timezone.utc)).days, 0)
            score += max(0, 7 - age_days)
        score += min(title_counts[normalized_title(article.title)], 4) * 2
        article.score = max(score, 0.0)
    return sorted(articles, key=lambda item: (item.score, item.published or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)


def group_for_sections(articles: list[Article]) -> dict[str, list[Article]]:
    sections: dict[str, list[Article]] = {section: [] for section in SECTION_ORDER}
    for article in articles:
        section = SECTION_ALIASES.get(article.category, article.category)
        if section in sections:
            sections[section].append(article)
    return sections


def classroom_connections(articles: list[Article], limit: int = 4) -> list[Connection]:
    connections: list[Connection] = []
    for article in articles:
        text = f"{article.title} {article.summary} {article.category}".lower()
        for label, terms in CLASSROOM_TERMS.items():
            if any(term in text for term in terms):
                connections.append(Connection(article.title, article.url, classroom_explanation(label), label))
                break
        if len(connections) >= limit:
            break
    return connections


def ministry_connections(articles: list[Article], limit: int = 4) -> list[Connection]:
    connections: list[Connection] = []
    for article in articles:
        text = f"{article.title} {article.summary} {article.category}".lower()
        if article.category in {"Theology", "Biblical Studies", "Church Leadership"} or any(term in text for term in MINISTRY_TERMS):
            connections.append(Connection(article.title, article.url, "Useful for Bible teaching, theological reflection, church leadership, or cultural engagement.", "Ministry"))
        if len(connections) >= limit:
            break
    return connections


def choose_book(books: list[Book], generated_at: datetime) -> Book | None:
    if not books:
        return None
    cycle = ["Theology", "History", "Science", "Fantasy"]
    category = cycle[generated_at.toordinal() % len(cycle)]
    candidates = [book for book in books if book.category == category] or books
    index_seed = int(hashlib.sha256(generated_at.strftime("%Y-%m-%d").encode()).hexdigest(), 16)
    return candidates[index_seed % len(candidates)]


def render_page(
    generated_at: datetime,
    top_story: Article | None,
    sections: dict[str, list[Article]],
    classroom: list[Connection],
    ministry: list[Connection],
    book: Book | None,
    article_count: int,
    feed_count: int,
    feed_errors: list[str],
) -> str:
    template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{ title }}": "Bramer Briefing",
        "{{ date_label }}": generated_at.strftime("%A, %B %d, %Y"),
        "{{ generated_at }}": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "{{ reading_time }}": "5",
        "{{ article_count }}": str(article_count),
        "{{ feed_count }}": str(feed_count),
        "{{ top_story }}": render_top_story(top_story),
        "{{ section_nav }}": render_section_nav(),
        "{{ sections }}": render_sections(sections),
        "{{ classroom_connections }}": render_connections(classroom, "No classroom-specific connections were identified today."),
        "{{ ministry_connections }}": render_connections(ministry, "No ministry-specific connections were identified today."),
        "{{ book }}": render_book(book),
        "{{ feed_status }}": render_feed_status(feed_errors),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def render_top_story(article: Article | None) -> str:
    if article is None:
        return '<p class="empty">No articles were available. Check feed configuration or try again after the next scheduled build.</p>'
    return render_article(article, featured=True)


def render_section_nav() -> str:
    links = ['<a href="#top-story">Top Story</a>']
    links.extend(f'<a href="#{slug(section)}">{escape(section)}</a>' for section in SECTION_ORDER)
    links.extend(['<a href="#classroom">Classroom</a>', '<a href="#ministry">Ministry</a>', '<a href="#book">Book</a>'])
    return "\n    ".join(links)


def render_sections(sections: dict[str, list[Article]]) -> str:
    blocks: list[str] = []
    for section in SECTION_ORDER:
        articles = sections.get(section, [])[:3]
        body = '<p class="empty">No high-priority story made this section today.</p>' if not articles else '<div class="article-grid">' + "\n".join(render_article(article) for article in articles) + "</div>"
        blocks.append(f'''<section class="section" id="{slug(section)}">
  <div class="section-heading"><p class="eyebrow">{escape(section)}</p><h2>{escape(section)}</h2></div>
  {body}
</section>''')
    return "\n".join(blocks)


def render_article(article: Article, featured: bool = False) -> str:
    classes = "article-card featured" if featured else "article-card"
    return f'''<article class="{classes}">
  <div class="article-meta"><span>{escape(article.source)}</span><span>{format_date(article.published)}</span><span>{escape(article.category)}</span></div>
  <h3><a href="{escape(article.url)}">{escape(article.title)}</a></h3>
  <p>{escape(article.summary)}</p>
</article>'''


def render_connections(connections: list[Connection], empty_text: str) -> str:
    if not connections:
        return f'<p class="empty">{escape(empty_text)}</p>'
    return "\n".join(f'''<article class="mini-card">
  <p class="connection-label">{escape(item.label)}</p>
  <h3><a href="{escape(item.url)}">{escape(item.title)}</a></h3>
  <p>{escape(item.explanation)}</p>
</article>''' for item in connections)


def render_book(book: Book | None) -> str:
    if book is None:
        return '<p class="empty">No book recommendations are configured.</p>'
    return f'''<div class="book-card">
  <p class="connection-label">{escape(book.category)}</p>
  <h3>{escape(book.title)}</h3>
  <p class="byline">{escape(book.author)}</p>
  <p>{escape(book.note)}</p>
</div>'''


def render_feed_status(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{escape(error)}</li>" for error in errors)
    label = "feed issue" if len(errors) == 1 else "feed issues"
    return f"<details><summary>{len(errors)} {label}</summary><ul>{items}</ul></details>"


def classroom_explanation(label: str) -> str:
    return {
        "ICP": "A current-event hook for scientific inquiry, matter, energy, or systems thinking.",
        "Physical Science": "A real-world connection to energy, waves, forces, motion, or matter.",
        "Chemistry": "A useful example for atoms, reactions, materials, or molecular structure.",
        "Physics": "A timely connection to motion, momentum, energy, gravity, space, or modern physics.",
    }[label]


def one_sentence(text: str, limit: int = 240) -> str:
    cleaned = clean_text(text)
    match = re.search(r"(.+?[.!?])\s", cleaned)
    sentence = match.group(1) if match else cleaned
    if len(sentence) <= limit:
        return sentence
    return sentence[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def clean_text(value: str) -> str:
    without_tags = TAG_RE.sub(" ", html.unescape(value or ""))
    return SPACE_RE.sub(" ", without_tags).strip()


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def normalized_title(title: str) -> str:
    return SPACE_RE.sub(" ", title.lower()).strip()[:120]


def format_date(value: datetime | None) -> str:
    if value is None:
        return "Recent"
    return value.astimezone(timezone.utc).strftime("%b %d, %Y")


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


if __name__ == "__main__":
    main()
