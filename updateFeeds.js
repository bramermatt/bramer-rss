const Parser = require("rss-parser");
const fs = require("fs");

const parser = new Parser();

const FEEDS = {
    Science: [
        "https://phys.org/rss-feed/",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://www.livescience.com/feeds/all"
    ],

    Space: [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.space.com/feeds/all",
        "https://www.planetary.org/rss.xml"
    ],

    AI: [
        "https://openai.com/news/rss.xml",
        "https://hnrss.org/frontpage",
        "http://feeds.arstechnica.com/arstechnica/index"
    ],

    Theology: [
        "https://www.thegospelcoalition.org/feed/",
        "https://www.9marks.org/feed/",
        "https://www.ligonier.org/posts/rss"
    ],

    "Biblical Studies": [
        "https://www.biblicalarchaeology.org/feed/"
    ],

    History: [
        "https://allthingsliberty.com/feed/",
        "https://www.historynet.com/feed/"
    ]
};

async function updateFeeds() {

    const articles = [];

    for (const [category, urls] of Object.entries(FEEDS)) {

        for (const url of urls) {

            try {

                console.log(`Loading ${category}: ${url}`);

                const feed = await parser.parseURL(url);

                feed.items.slice(0, 3).forEach(item => {

                    articles.push({
                        category,
                        title: item.title || "",
                        source: feed.title || category,
                        date: item.pubDate || item.isoDate || "",
                        summary:
                            item.contentSnippet ||
                            item.summary ||
                            "",
                        url: item.link || "#"
                    });

                });

                console.log(`✓ ${feed.title}`);

            } catch (err) {

                console.error(`✗ Failed: ${url}`);
                console.error(err.message);

            }
        }
    }

    articles.sort(
        (a, b) =>
            new Date(b.date) - new Date(a.date)
    );

    const output = {
        lastUpdated: new Date().toISOString(),
        articleCount: articles.length,
        articles
    };

    fs.writeFileSync(
        "articles.json",
        JSON.stringify(output, null, 2)
    );

    console.log(`Saved ${articles.length} articles.`);
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