const Parser = require("rss-parser");
const fs = require("fs");

const parser = new Parser();

const FEEDS = [
    {
        category: "Science",
        url: "https://phys.org/rss-feed/"
    },
    {
        category: "Theology",
        url: "https://www.thegospelcoalition.org/feed/"
    },
    {
    category: "Space",
    url: "https://www.nasa.gov/rss/dyn/breaking_news.rss"
    },
    {
    category: "AI",
    url: "https://openai.com/news/rss.xml"
    },
    {
    category: "History",
    url: "https://allthingsliberty.com/feed/"
    }
    
];

async function updateFeeds() {
    const articles = [];

for (const feedInfo of FEEDS) {

    try {

        console.log(`Loading ${feedInfo.category}...`);

        const feed = await parser.parseURL(feedInfo.url);

        feed.items.slice(0, 5).forEach(item => {

            articles.push({
                category: feedInfo.category,
                title: item.title,
                source: feed.title,
                date: item.pubDate,
                summary: item.contentSnippet,
                url: item.link
            });

        });

        console.log(`✓ ${feedInfo.category}`);

    } catch (err) {

        console.error(
            `✗ Failed: ${feedInfo.category}`,
            err.message
        );

    }
}

const output = {
    lastUpdated: new Date().toISOString(),
    articles: articles
};

fs.writeFileSync(
    "articles.json",
    JSON.stringify(output, null, 2)
);
}

updateFeeds()
    .then(() => {
        console.log("Done.");
        process.exit(0);
    })
    .catch(err => {
        console.error(err);
        process.exit(1);
    });