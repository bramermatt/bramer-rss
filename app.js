async function loadArticles() {
    const response = await fetch("articles.json");
    const data = await response.json();

    renderArticles(
        data.articles,
        data.lastUpdated
    );
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

    const card = document.createElement("article");

    card.className = "article-card";

    card.innerHTML = `
        <h3>
            <a href="${article.url}" target="_blank">
                ${article.title}
            </a>
        </h3>

        <div class="meta">
            ${article.source} • ${formatDate(article.date)}
        </div>
    `;

    topStories.appendChild(card);
});

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

content.appendChild(topStories);

// Categories

Object.entries(categories).forEach(([category, items]) => {

    const id = category.toLowerCase();

    const navLink = document.createElement("a");

    navLink.href = `#${id}`;
    navLink.textContent = category;

    nav.appendChild(navLink);

    const section = document.createElement("section");

    section.id = id;

    section.innerHTML = `
        <h2>${category}</h2>
    `;

    items.forEach(article => {

        const articleElement = document.createElement("article");

        articleElement.className = "article-card";

        articleElement.innerHTML = `
            <h3>
                <a href="${article.url}" target="_blank">
                    ${article.title}
                </a>
            </h3>

            <div class="meta">
                ${article.source}
            </div>

            <p>${article.summary || ""}</p>
        `;

        section.appendChild(articleElement);
    });

    content.appendChild(section);
});

}


loadArticles();