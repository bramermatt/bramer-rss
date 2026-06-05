"""Web routes for the Bramer Briefing dashboard."""
from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from bramer_briefing.feeds.reader import fetch_feeds
from bramer_briefing.models import Article, Briefing, SavedArticle, UserPreference, db
from bramer_briefing.services.briefings import briefing_context, generate_briefing

bp = Blueprint("main", __name__)


@bp.get("/")
def dashboard():
    return render_template("dashboard.html", **briefing_context())


@bp.get("/briefing")
def today_briefing():
    return render_template("briefing.html", **briefing_context())


@bp.post("/briefing/generate")
def generate_today_briefing():
    generate_briefing()
    flash("Generated a fresh briefing.", "success")
    return redirect(url_for("main.today_briefing"))


@bp.get("/articles")
def articles():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    articles_query = Article.query
    if query:
        like = f"%{query}%"
        articles_query = articles_query.filter(or_(Article.title.ilike(like), Article.source.ilike(like), Article.category.ilike(like)))
    if category:
        articles_query = articles_query.filter_by(category=category)
    items = articles_query.order_by(Article.relevance_score.desc()).limit(200).all()
    categories = [row[0] for row in db.session.query(Article.category).distinct().order_by(Article.category).all()]
    return render_template("articles.html", articles=items, categories=categories, query=query, selected_category=category)


@bp.get("/categories")
def categories():
    rows = db.session.query(Article.category, func.count(Article.id)).group_by(Article.category).order_by(Article.category).all()
    return render_template("categories.html", rows=rows)


@bp.post("/articles/<int:article_id>/save")
def save_article(article_id: int):
    if not SavedArticle.query.filter_by(article_id=article_id).first():
        db.session.add(SavedArticle(article_id=article_id))
        db.session.commit()
        flash("Article saved.", "success")
    return redirect(request.referrer or url_for("main.articles"))


@bp.get("/saved")
def saved_articles():
    saved = SavedArticle.query.order_by(SavedArticle.saved_at.desc()).all()
    return render_template("saved.html", saved=saved)


@bp.get("/history")
def history():
    briefings = Briefing.query.order_by(Briefing.generated_at.desc()).all()
    return render_template("history.html", briefings=briefings)


@bp.get("/history/<int:briefing_id>")
def history_detail(briefing_id: int):
    briefing = Briefing.query.get_or_404(briefing_id)
    return render_template("briefing.html", **briefing_context(briefing))


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        for pref in UserPreference.query.all():
            pref.weight = int(request.form.get(pref.category, pref.weight))
        db.session.commit()
        flash("Settings updated.", "success")
        return redirect(url_for("main.settings"))
    preferences = UserPreference.query.order_by(UserPreference.category).all()
    return render_template("settings.html", preferences=preferences)


@bp.post("/refresh")
def refresh():
    count = fetch_feeds(current_app.config["FEEDS_CONFIG"])
    generate_briefing()
    flash(f"Fetched {count} new articles and regenerated the briefing.", "success")
    return redirect(url_for("main.dashboard"))
