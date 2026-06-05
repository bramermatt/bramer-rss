"""Database models for Bramer Briefing."""
from __future__ import annotations

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint


db = SQLAlchemy()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    source = db.Column(db.String(255), nullable=False, default="Unknown")
    url = db.Column(db.String(1000), nullable=False, unique=True)
    summary = db.Column(db.Text, nullable=True)
    publication_date = db.Column(db.DateTime(timezone=True), nullable=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    relevance_score = db.Column(db.Float, nullable=False, default=0.0, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    saved = db.relationship("SavedArticle", back_populates="article", cascade="all, delete-orphan")


class Briefing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    estimated_read_time = db.Column(db.Integer, nullable=False, default=5)
    top_article_id = db.Column(db.Integer, db.ForeignKey("article.id"), nullable=True)

    top_article = db.relationship("Article")
    items = db.relationship("BriefingItem", back_populates="briefing", cascade="all, delete-orphan", order_by="BriefingItem.position")


class BriefingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    briefing_id = db.Column(db.Integer, db.ForeignKey("briefing.id"), nullable=False, index=True)
    article_id = db.Column(db.Integer, db.ForeignKey("article.id"), nullable=False)
    section = db.Column(db.String(100), nullable=False)
    position = db.Column(db.Integer, nullable=False)

    briefing = db.relationship("Briefing", back_populates="items")
    article = db.relationship("Article")


class SavedArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("article.id"), nullable=False)
    saved_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    article = db.relationship("Article", back_populates="saved")
    __table_args__ = (UniqueConstraint("article_id", name="uq_saved_article"),)


class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False, unique=True)
    weight = db.Column(db.Integer, nullable=False, default=5)


class BookRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    last_recommended_at = db.Column(db.DateTime(timezone=True), nullable=True)
