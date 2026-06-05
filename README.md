# Bramer Briefing

Bramer Briefing is a local Flask web application that turns RSS feeds into a curated personal intelligence dashboard and five-minute digital newspaper for science teaching, Bible study, ministry, history, books, AI, and technology.

## Project architecture

```text
bramer_briefing/
  config/          YAML feed and book recommendation samples
  feeds/           RSS loading, parsing, cleanup, and deduplication
  scoring/         Relevance ranking rules and category weights
  services/        Briefing generation, books, classroom/ministry connections
  templates/       Jinja2 pages for the newspaper-style web UI
  static/          Responsive light/dark CSS
  models.py        SQLite/SQLAlchemy models
  routes.py        Flask page and action routes
  cli.py           Flask CLI commands
main.py            Local app entrypoint
tests/             Pytest unit tests
```

## Database design

The app uses SQLite through SQLAlchemy. It creates these tables:

- `Article`: title, source, URL, summary, publication date, category, relevance score, and creation timestamp.
- `Briefing`: generated timestamp, estimated reading time, and top story.
- `BriefingItem`: ordered article membership for each generated briefing.
- `SavedArticle`: read-later records.
- `UserPreference`: category weight settings used during scoring.
- `BookRecommendation`: local book rotation with last recommendation tracking.

## Feed ingestion workflow

1. Edit `bramer_briefing/config/feeds.yaml`.
2. Run `flask --app main fetch-feeds` or use **Fetch Feeds & Generate Briefing** in the dashboard.
3. The app downloads each RSS feed, handles failed/empty feeds gracefully, cleans HTML descriptions with BeautifulSoup, canonicalizes URLs, skips duplicate URLs, stores new articles, and rescans relevance scores.

## Ranking workflow

Ranking starts with the category weight from Settings. Positive terms such as `breakthrough`, `discovery`, `mission`, `archaeology`, `release`, and `teaching` raise the score. Negative terms such as `celebrity`, `sponsored`, `sale`, `rumor`, and clickbait phrases lower the score. Recent publication dates receive a small freshness boost, and similar titles can receive a multi-source boost.

## Installation

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app main rebuild-db
```

## Running locally

```bash
flask --app main run --debug
```

Open <http://127.0.0.1:5000>.

## CLI commands

```bash
flask --app main fetch-feeds          # Download configured RSS feeds
flask --app main refresh-articles     # Re-score articles after rule or preference changes
flask --app main generate-briefing    # Create a new five-minute briefing
flask --app main rebuild-db           # Recreate the local SQLite database
python main.py                        # Run the development server
```

## Adding feeds

Add feeds to `bramer_briefing/config/feeds.yaml` under any category:

```yaml
categories:
  Physics:
    - name: Example Physics Feed
      url: https://example.com/rss.xml
```

Categories are configurable. New category names will appear in article search and category pages after feed ingestion.

## Web pages

- Dashboard
- Today's Briefing
- All Articles with search by title, source, and category
- Categories
- Saved Articles
- Briefing History
- Settings for category weighting

## Recommended Version 2 features

- LLM-generated article summaries and connection explanations.
- Semantic search and personalized ranking.
- Daily email delivery.
- Text-to-speech and podcast generation.
- Reading analytics and saved-reading notes.
- Mobile-first progressive web app features.
