# Bramer Briefing

Bramer Briefing is now a **simple static HTML briefing generator**. It has no Flask app, no SQLite database, no web server, and no required third-party packages.

Run one Python script, fetch RSS/Atom feeds, and generate a responsive mobile-friendly HTML page that answers:

> If I only have five minutes today, what should I know?

## What it does

- Uses built-in RSS/Atom feed lists for science, space, AI, education, theology, biblical studies, church leadership, history, and books.
- Optionally reads a tiny YAML-like feed file.
- Downloads feeds with Python's standard library.
- Parses recent RSS/Atom entries.
- Removes duplicate URLs.
- Scores stories with simple keyword, category-weight, freshness, and duplicate-title signals.
- Writes a single static HTML file with:
  - Top Story
  - Category sections
  - Classroom Connections
  - Faith & Ministry Connections
  - Feed status notes
  - Responsive mobile-first styling
  - Automatic dark-mode support

## Requirements

- Python 3.12+
- No required Python packages beyond the standard library

## Generate the briefing

```bash
python main.py
```

The default output is:

```text
output/bramer-briefing.html
```

Open that file in your browser.

## Useful commands

Generate to a custom path:

```bash
python main.py --output briefing.html
```

Limit the number of curated stories:

```bash
python main.py --max-stories 10
```

Show detailed fetch logging:

```bash
python main.py --verbose
```

Use a custom feed file:

```bash
python main.py --feeds my-feeds.yaml --output output/today.html
```

## Optional custom feed file

The script supports a simple YAML-like format without requiring PyYAML:

```yaml
Science:
  - https://www.sciencedaily.com/rss/all.xml
AI:
  - https://openai.com/news/rss.xml
Theology:
  - https://www.thegospelcoalition.org/feed/
```

## How ranking works

Every article starts with a category weight. Teacher/ministry priorities such as theology, biblical studies, science, physics, chemistry, space, and education start higher than general technology or books. The script then adjusts the score:

- Adds points for terms like `breakthrough`, `discovery`, `mission`, `archaeology`, `release`, `teaching`, and `ministry`.
- Subtracts points for terms like `celebrity`, `sponsored`, `sale`, `rumor`, and clickbait phrases.
- Adds a freshness boost for recently published stories.
- Adds a small boost if the same title appears more than once.

## Project files

```text
main.py           # The complete static HTML briefing generator
requirements.txt  # Documents that no third-party packages are required
README.md         # Usage documentation
```

## Why this version is simpler

The previous implementation was a full Flask/SQLite web application. This version intentionally removes that complexity and returns to a single-purpose local tool: run a script, get a clean static briefing page, and read it anywhere.
