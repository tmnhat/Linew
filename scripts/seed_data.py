"""
Seed data - 53 RSS sources and default settings.
"""
import asyncio
import logging

from app.core.database import get_db_context
from app.models.source import Source
from app.models.setting import Setting, DEFAULT_SETTINGS
from sqlalchemy import select

logger = logging.getLogger(__name__)

# 53 RSS Sources
RSS_SOURCES = [
    # US Tech (10)
    {"name": "TechCrunch", "feed_url": "https://techcrunch.com/feed/", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Verge", "feed_url": "https://www.theverge.com/rss/index.xml", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Ars Technica", "feed_url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Wired", "feed_url": "https://www.wired.com/feed/rss", "category_hint": "tech", "language": "en", "crawl_difficulty": "medium"},
    {"name": "MIT Technology Review", "feed_url": "https://www.technologyreview.com/feed/", "category_hint": "tech", "language": "en", "crawl_difficulty": "medium"},
    {"name": "Hacker News Best", "feed_url": "https://hnrss.org/best", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "VentureBeat", "feed_url": "https://venturebeat.com/feed/", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "IEEE Spectrum", "feed_url": "https://spectrum.ieee.org/feeds/feed.rss", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "ZDNet", "feed_url": "https://www.zdnet.com/news/rss.xml", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Information", "feed_url": "https://www.theinformation.com/feed", "category_hint": "tech", "language": "en", "crawl_difficulty": "hard"},

    # US Finance (6)
    {"name": "Bloomberg Tech", "feed_url": "https://feeds.bloomberg.com/technology/news.rss", "category_hint": "finance", "language": "en", "crawl_difficulty": "hard"},
    {"name": "CNBC Tech", "feed_url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "MarketWatch", "feed_url": "https://feeds.marketwatch.com/marketwatch/topstories/", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Yahoo Finance", "feed_url": "https://finance.yahoo.com/news/rssindex", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "CoinDesk", "feed_url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Reuters Business", "feed_url": "https://www.reutersagency.com/feed/", "category_hint": "finance", "language": "en", "crawl_difficulty": "medium"},

    # UK (6)
    {"name": "BBC Technology", "feed_url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "BBC Business", "feed_url": "https://feeds.bbci.co.uk/news/business/rss.xml", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Guardian Tech", "feed_url": "https://www.theguardian.com/uk/technology/rss", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Financial Times", "feed_url": "https://www.ft.com/technology?format=rss", "category_hint": "finance", "language": "en", "crawl_difficulty": "hard"},
    {"name": "The Register", "feed_url": "https://www.theregister.com/headlines.atom", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "TechRadar", "feed_url": "https://www.techradar.com/rss", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},

    # Germany (4)
    {"name": "Heise Online", "feed_url": "https://www.heise.de/rss/heise-atom.xml", "category_hint": "tech", "language": "de", "crawl_difficulty": "easy"},
    {"name": "Golem.de", "feed_url": "https://rss.golem.de/rss.php?feed=RSS2.0", "category_hint": "tech", "language": "de", "crawl_difficulty": "easy"},
    {"name": "Handelsblatt Tech", "feed_url": "https://www.handelsblatt.com/contentexport/feed/technik", "category_hint": "finance", "language": "de", "crawl_difficulty": "medium"},
    {"name": "T3N", "feed_url": "https://t3n.de/rss.xml", "category_hint": "tech", "language": "de", "crawl_difficulty": "easy"},

    # France (3)
    {"name": "Les Echos Tech", "feed_url": "https://www.lesechos.fr/rss/rss_une_tech_medias.xml", "category_hint": "tech", "language": "fr", "crawl_difficulty": "medium"},
    {"name": "Le Monde Tech", "feed_url": "https://www.lemonde.fr/pixels/rss_full.xml", "category_hint": "tech", "language": "fr", "crawl_difficulty": "medium"},
    {"name": "01Net", "feed_url": "https://www.01net.com/rss/info/flux-rss/flux-toutes-les-actualites/", "category_hint": "tech", "language": "fr", "crawl_difficulty": "easy"},

    # Russia (3)
    {"name": "Habr", "feed_url": "https://habr.com/ru/rss/best/daily/", "category_hint": "tech", "language": "ru", "crawl_difficulty": "easy"},
    {"name": "RBC Technology", "feed_url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss", "category_hint": "tech", "language": "ru", "crawl_difficulty": "easy"},
    {"name": "TASS Science", "feed_url": "https://tass.com/rss/v2.xml", "category_hint": "tech", "language": "ru", "crawl_difficulty": "medium"},

    # China (5)
    {"name": "36Kr", "feed_url": "https://36kr.com/feed", "category_hint": "tech", "language": "zh", "crawl_difficulty": "medium", "requires_flaresolverr": True},
    {"name": "SCMP Technology", "feed_url": "https://www.scmp.com/rss/318/feed", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Caixin Tech", "feed_url": "https://www.caixinglobal.com/rss.html", "category_hint": "finance", "language": "en", "crawl_difficulty": "hard"},
    {"name": "TechNode", "feed_url": "https://technode.com/feed/", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "PingWest", "feed_url": "https://en.pingwest.com/feed", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},

    # Japan & Korea & India (6)
    {"name": "Nikkei Asia Tech", "feed_url": "https://asia.nikkei.com/rss/feed/nar", "category_hint": "tech", "language": "en", "crawl_difficulty": "medium"},
    {"name": "Japan Times Business", "feed_url": "https://www.japantimes.co.jp/feed/", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Korea Herald Tech", "feed_url": "https://www.koreaherald.com/rss/020200000000.xml", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "ZDNet Korea", "feed_url": "https://zdnet.co.kr/rss/", "category_hint": "tech", "language": "ko", "crawl_difficulty": "easy"},
    {"name": "Economic Times Tech", "feed_url": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "LiveMint Tech", "feed_url": "https://www.livemint.com/rss/technology", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},

    # Crypto (2)
    {"name": "The Block", "feed_url": "https://www.theblock.co/rss.xml", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Decrypt", "feed_url": "https://decrypt.co/feed", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},

    # Vietnam (8)
    {"name": "VnExpress Số hóa", "feed_url": "https://vnexpress.net/rss/so-hoa.rss", "category_hint": "tech", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "VnExpress Kinh doanh", "feed_url": "https://vnexpress.net/rss/kinh-doanh.rss", "category_hint": "finance", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "Thanh Niên Công nghệ", "feed_url": "https://thanhnien.vn/rss/cong-nghe.rss", "category_hint": "tech", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "CafeF", "feed_url": "https://cafef.vn/rss/trang-chu.rss", "category_hint": "finance", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "VnEconomy", "feed_url": "https://vneconomy.vn/rss/cong-nghe.rss", "category_hint": "tech", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "Dân Trí Công nghệ", "feed_url": "https://dantri.com.vn/rss/suc-manh-so.rss", "category_hint": "tech", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "VietnamNet Công nghệ", "feed_url": "https://vietnamnet.vn/rss/cong-nghe.rss", "category_hint": "tech", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "GenK", "feed_url": "https://genk.vn/rss/tin-moi-nhat.rss", "category_hint": "tech", "language": "vi", "crawl_difficulty": "easy"},
]


async def seed_sources():
    """Seed RSS sources."""
    async with get_db_context() as session:
        # Check if already seeded
        result = await session.execute(select(Source).limit(1))
        if result.scalar_one_or_none():
            logger.info("Sources already seeded, skipping")
            return

        # Seed sources
        for source_data in RSS_SOURCES:
            source = Source(
                name=source_data["name"],
                feed_url=source_data["feed_url"],
                category_hint=source_data.get("category_hint"),
                language=source_data.get("language", "en"),
                crawl_difficulty=source_data.get("crawl_difficulty", "easy"),
                requires_flaresolverr=source_data.get("requires_flaresolverr", False),
                is_active=True,
            )
            session.add(source)

        await session.commit()
        logger.info(f"Seeded {len(RSS_SOURCES)} RSS sources")


async def seed_settings():
    """Seed default settings."""
    async with get_db_context() as session:
        for key, value in DEFAULT_SETTINGS.items():
            result = await session.execute(select(Setting).where(Setting.key == key))
            if not result.scalar_one_or_none():
                setting = Setting(key=key, value=value)
                session.add(setting)

        await session.commit()
        logger.info("Seeded default settings")


async def seed_all():
    """Seed all initial data."""
    logger.info("Starting seed process...")
    await seed_settings()
    await seed_sources()
    logger.info("Seed completed!")


if __name__ == "__main__":
    asyncio.run(seed_all())
