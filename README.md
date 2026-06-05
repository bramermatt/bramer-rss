# Bramer Briefing

Bramer Briefing is a static personal daily news website. It automatically builds a curated five-minute briefing from RSS feeds and publishes the latest `index.html` through GitHub Actions and GitHub Pages.

There is no Flask, FastAPI, SQLite, authentication, database, user account system, or web server. The finished site is just static HTML and CSS.

## What the site answers

> If I only have five minutes today, what should I know?

The briefing is designed for a high school science teacher, Bible teacher, preacher, lifelong reader, and technology enthusiast who follows science, space, AI, education, theology, biblical studies, church leadership, American history, books, and fantasy literature.

## How it works

Every day, GitHub Actions:

1. Checks out the repository.
2. Verifies the Python environment (the generator uses only the standard library).
3. Reads RSS feeds from `config/feeds.yml`.
4. Downloads and processes recent articles.
5. Ranks the stories by relevance and importance.
6. Generates `public/index.html` plus static assets.
7. Deploys the generated site to GitHub Pages.

After setup, you do not need to manually run scripts, manage a server, or maintain infrastructure.

## Project structure

```text
.github/workflows/pages.yml   # Daily GitHub Actions build and Pages deployment
bramer_briefing/              # Python static-site generation package
  generator.py                # Feed fetching, ranking, connection logic, HTML rendering
  models.py                   # Small dataclasses used by the generator
config/
  feeds.yml                   # RSS feed configuration
  books.yml                   # Book of the Day rotation data
templates/
  index.html                  # Main HTML template
static/styles.css             # Mobile-first digital newspaper styling
main.py                       # Entrypoint used by GitHub Actions
requirements.txt              # Notes that no third-party runtime packages are required
tests/                        # Lightweight generator tests
```

## GitHub Pages setup

1. Push this repository to GitHub.
2. In GitHub, open **Settings → Pages**.
3. Under **Build and deployment**, choose **GitHub Actions** as the source.
4. Commit or manually run the workflow once from **Actions → Build and publish Bramer Briefing → Run workflow**.
5. Visit the GitHub Pages URL shown by the workflow deployment.

The workflow also runs every day at 10:00 UTC and republishes the latest briefing automatically.

## Feed configuration

Feeds live in `config/feeds.yml`. Add or remove feeds by editing category lists:

```yaml
Science:
  - name: ScienceDaily
    url: https://www.sciencedaily.com/rss/all.xml
AI:
  - name: OpenAI News
    url: https://openai.com/news/rss.xml
```

The included sample configuration covers ScienceDaily, Phys.org, NASA, The Planetary Society, OpenAI, Anthropic, Ars Technica AI, Edutopia, Education Week, The Gospel Coalition, 9Marks, Ligonier, Logos, Biblical Archaeology Society, Journal of the American Revolution, and Literary Hub.

## Briefing sections

The generated homepage includes:

- Top Story
- Science
- Space
- AI
- Education
- Theology
- History
- Books
- Classroom Connections
- Faith & Ministry Connections
- Book of the Day
- Feed status details when any feed fails

Each story includes a headline, source, publication date, one-sentence summary, and link to the original article.

## Book of the Day

Book recommendations live in `config/books.yml`. The generator rotates among:

- Theology
- History
- Science
- Fantasy

Add books by editing the appropriate category list.

## Local preview, optional

You do not need local commands after GitHub Pages is configured. If you want to preview locally before pushing, run:

```bash
python main.py --output public
```

Then open `public/index.html` in a browser.

## Ranking model

The ranking model is intentionally simple and transparent:

- Category weights prioritize theology, biblical studies, science, physics, chemistry, space, education, history, AI, and ministry-relevant stories.
- Positive keywords reward breakthroughs, discoveries, missions, launches, archaeology, teaching, ministry, and historical significance.
- Negative keywords reduce low-information stories, clickbait, celebrity content, rumors, and marketing-heavy items.
- Recent stories receive a freshness boost.
- Similar titles receive a small multi-source boost.

The scoring logic is in `bramer_briefing/generator.py` and can be tuned without changing the publishing workflow.
