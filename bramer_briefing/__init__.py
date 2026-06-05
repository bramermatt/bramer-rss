"""Application factory for Bramer Briefing."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from .models import db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    repo_root = Path(__file__).resolve().parent.parent
    app.config.from_mapping(
        SECRET_KEY="dev-change-me",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{repo_root / 'instance' / 'bramer_briefing.sqlite'}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        FEEDS_CONFIG=str(repo_root / "bramer_briefing" / "config" / "feeds.yaml"),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    @app.context_processor
    def inject_now():
        from datetime import datetime, timezone
        return {"now": lambda: datetime.now(timezone.utc)}


    from .routes import bp as main_bp
    from .cli import register_cli

    app.register_blueprint(main_bp)
    register_cli(app)

    with app.app_context():
        db.create_all()
        from .services.books import seed_default_books
        from .services.preferences import seed_default_preferences

        seed_default_preferences()
        seed_default_books()

    return app
