from __future__ import annotations

from bramer_briefing.models import Article

CLASSROOM_TERMS = {
    "ICP": ["science", "matter", "energy", "experiment", "climate"],
    "Physical Science": ["force", "motion", "energy", "waves", "electricity"],
    "Chemistry": ["chemistry", "molecule", "reaction", "element", "compound"],
    "Physics": ["physics", "space", "orbit", "momentum", "quantum", "telescope"],
}
MINISTRY_TERMS = ["bible", "theology", "church", "ministry", "pastor", "archaeology", "culture", "discipleship"]


def classroom_connections(articles: list[Article], limit: int = 4) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for article in articles:
        text = f"{article.title} {article.summary or ''} {article.category}".lower()
        for course, terms in CLASSROOM_TERMS.items():
            if any(term in text for term in terms):
                results.append({
                    "title": article.title,
                    "url": article.url,
                    "relevance": f"Useful for {course} because it connects current events with observable science.",
                    "concept": _concept_for(course),
                })
                break
        if len(results) >= limit:
            break
    return results


def ministry_connections(articles: list[Article], limit: int = 4) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for article in articles:
        text = f"{article.title} {article.summary or ''} {article.category}".lower()
        if article.category in {"Theology", "Biblical Studies", "Church Leadership"} or any(term in text for term in MINISTRY_TERMS):
            results.append({
                "title": article.title,
                "url": article.url,
                "explanation": "This story may support Bible teaching, theological reflection, church leadership, or cultural engagement.",
            })
        if len(results) >= limit:
            break
    return results


def _concept_for(course: str) -> str:
    return {
        "ICP": "Scientific inquiry, matter, energy, and real-world observation.",
        "Physical Science": "Forces, energy transfer, waves, or systems thinking.",
        "Chemistry": "Atomic structure, reactions, bonding, or materials science.",
        "Physics": "Motion, momentum, gravity, energy, or modern physics.",
    }[course]
