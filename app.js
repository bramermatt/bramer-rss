

async function loadArticles() {
    const response = await fetch("articles.json");
    const data = await response.json();

    renderArticles(
        data.articles,
        data.lastUpdated
    );
}

const categoryIcons = {
    AI: "🤖",
    Science: "🔬",
    Space: "🚀",
    Tech: "💻",
    Business: "📈",
    Health: "🩺",
    Culture: "🎨",
    World: "🌍",
    Design: "🎨",
    Default: "📰"
};

function getSiteFaviconUrl(articleUrl) {
    try {
        const sourceUrl = new URL(articleUrl);
        return `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(sourceUrl.origin)}`;
    } catch (error) {
        return "";
    }
}

function getArticleThumbnail(article) {
    if (article.thumbnail && article.thumbnail.trim()) {
        return article.thumbnail;
    }

    if (article.image && article.image.trim()) {
        return article.image;
    }

    return "";
}

async function fetchPreviewImageFromUrl(articleUrl) {
    if (!articleUrl) {
        return "";
    }

    try {
        const normalized = articleUrl.replace(/^https?:\/\//i, "");
        const jinaUrl = `https://r.jina.ai/http://${normalized}`;
        const response = await fetch(jinaUrl, {
            headers: { Accept: "text/plain" }
        });

        if (!response.ok) {
            return "";
        }

        const text = await response.text();

        const metaImageMatch = text.match(
            /(?:og:image|twitter:image)[^\n]*https?:\/\/[^\s"'<>]+/i
        ) || text.match(/https?:\/\/[^\s"'<>]+\.(?:png|jpe?g|webp|gif|avif|svg)(?:\?[^\s"'<>]*)?/i);

        if (metaImageMatch) {
            const extracted = metaImageMatch[0].trim();
            return extracted.replace(/.*(?:content|url)=['"]?/, "").replace(/[),.;]+$/, "") || "";
        }

        const markdownImageMatch = text.match(
            /!\[[^\]]*\]\((https?:\/\/[^\s)]+)\)/i
        );

        if (markdownImageMatch) {
            return markdownImageMatch[1];
        }

        const directImageMatch = text.match(
            /https?:\/\/[^\s"'<>]+\.(?:png|jpe?g|webp|gif|avif|svg)(?:\?[^\s"'<>]*)?/i
        );

        return directImageMatch ? directImageMatch[0] : "";
    } catch (error) {
        return "";
    }
}

function getCategoryIcon(category) {
    const normalized = category || "Default";
    const key = Object.keys(categoryIcons).find(name =>
        normalized.toLowerCase() === name.toLowerCase()
    );

    return categoryIcons[key || "Default"] || categoryIcons.Default;
}

function formatDate(dateString) {

    const published = new Date(dateString);

    const hours =
        Math.floor(
            (Date.now() - published.getTime())
            / 1000 / 60 / 60
        );

    if (hours < 24) {
        return `${hours}h ago`;
    }

    const days = Math.floor(hours / 24);

    if (days < 7) {
        return `${days}d ago`;
    }

    return published.toLocaleDateString(
        "en-US",
        {
            month: "short",
            day: "numeric"
        }
    );
}

function createArticleCard(article, { showSummary = false } = {}) {
    const card = document.createElement("article");
    card.className = "article-card";

    const thumb = document.createElement("div");
    thumb.className = "article-thumb";

    const imageUrl = getArticleThumbnail(article);

    const renderFallback = () => {
        const fallbackUrl = getSiteFaviconUrl(article.url);
        const placeholder = document.createElement("div");
        placeholder.className = "article-thumb placeholder";
        placeholder.textContent = (article.source || "N").charAt(0).toUpperCase();

        if (fallbackUrl) {
            const faviconImg = document.createElement("img");
            faviconImg.src = fallbackUrl;
            faviconImg.alt = `${article.title} site favicon`;
            faviconImg.loading = "lazy";
            faviconImg.referrerPolicy = "no-referrer";
            thumb.innerHTML = "";
            thumb.appendChild(faviconImg);
            return;
        }

        thumb.innerHTML = "";
        thumb.appendChild(placeholder);
    };

    if (imageUrl) {
        const img = document.createElement("img");
        img.src = imageUrl;
        img.alt = `${article.title} thumbnail`;
        img.loading = "lazy";
        img.decoding = "async";
        img.referrerPolicy = "no-referrer";

        img.onerror = () => {
            renderFallback();
        };

        fetchPreviewImageFromUrl(article.url).then(previewUrl => {
            if (previewUrl && previewUrl !== img.src) {
                img.src = previewUrl;
            }
        });

        thumb.appendChild(img);
    } else {
        fetchPreviewImageFromUrl(article.url).then(previewUrl => {
            if (!previewUrl) {
                renderFallback();
                return;
            }

            const img = document.createElement("img");
            img.src = previewUrl;
            img.alt = `${article.title} thumbnail`;
            img.loading = "lazy";
            img.decoding = "async";
            img.referrerPolicy = "no-referrer";
            img.onerror = () => renderFallback();
            thumb.innerHTML = "";
            thumb.appendChild(img);
        });

        if (article.url) {
            const placeholder = document.createElement("div");
            placeholder.className = "article-thumb placeholder";
            placeholder.textContent = (article.source || "N").charAt(0).toUpperCase();
            thumb.appendChild(placeholder);
        }
    }

    const body = document.createElement("div");
    body.className = "article-body";

    const heading = document.createElement("h3");
    const link = document.createElement("a");
    link.href = article.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = article.title;
    heading.appendChild(link);
    body.appendChild(heading);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${article.source} • ${formatDate(article.date)}`;
    body.appendChild(meta);

    if (showSummary && article.summary) {
        const summary = document.createElement("p");
        summary.textContent = article.summary;
        body.appendChild(summary);
    }

    card.appendChild(thumb);
    card.appendChild(body);

    return card;
}

function renderArticles(articles, lastUpdated) {

const content = document.getElementById("content");
const nav = document.getElementById("nav");

document.getElementById("updated").textContent =
    "Last Updated: " +
    new Date(lastUpdated).toLocaleString();

content.innerHTML = "";
nav.innerHTML = "";

document.getElementById("today").textContent =
    new Date().toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric"
    });

// newest first
articles.sort(
    (a, b) => new Date(b.date) - new Date(a.date)
);

const categories = {};

articles.forEach(article => {
    if (!categories[article.category]) {
        categories[article.category] = [];
    }

    categories[article.category].push(article);
});

// Top Stories

const topStories = document.createElement("section");

topStories.innerHTML = `
    <h2>Top Stories</h2>
`;

articles.slice(0, 10).forEach(article => {
    topStories.appendChild(createArticleCard(article));
});

content.appendChild(topStories);

// Categories

Object.entries(categories).forEach(([category, items]) => {

    const id = category.toLowerCase();

    const navLink = document.createElement("a");

    navLink.href = `#${id}`;
    navLink.title = category;
    navLink.setAttribute("aria-label", category);
    navLink.innerHTML = `
        <span class="nav-icon" aria-hidden="true">${getCategoryIcon(category)}</span>
        <span class="nav-label">${category}</span>
    `;

    navLink.addEventListener("click", () => {
        nav.classList.remove("open");
        if (menuButton) {
            menuButton.classList.remove("open");
        }
    });

    nav.appendChild(navLink);

    const section = document.createElement("section");

    section.id = id;

    section.innerHTML = `
        <h2>${category}</h2>
    `;

    const sections = document.querySelectorAll("section");
    const navLinks = document.querySelectorAll("#nav a");

    window.addEventListener("scroll", () => {

        let current = "";

        sections.forEach(section => {

            const top = section.offsetTop - 120;

            if (window.scrollY >= top) {
                current = section.id;
            }
        });

        navLinks.forEach(link => {

            link.classList.remove("active");

            if (link.getAttribute("href") === `#${current}`) {
                link.classList.add("active");
            }

        });

    });

    items.forEach(article => {
        section.appendChild(createArticleCard(article, { showSummary: true }));
    });

    content.appendChild(section);
});

}

loadArticles();

const menuButton = document.getElementById("menu-button");
const nav = document.getElementById("nav");

if (menuButton && nav) {
    menuButton.addEventListener("click", () => {
        nav.classList.toggle("open");
        menuButton.classList.toggle("open");
    });
}