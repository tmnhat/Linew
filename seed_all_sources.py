#!/usr/bin/env python3
"""
Seed script to populate sources table with 58 news RSS feeds from around the world.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.core.database import async_session_maker


SOURCES = [
    # Major Crypto News
    {"name": "CoinDesk", "feed_url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "site_url": "https://www.coindesk.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "CoinTelegraph", "feed_url": "https://cointelegraph.com/rss", "site_url": "https://cointelegraph.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Block", "feed_url": "https://www.theblock.co/rss.xml", "site_url": "https://www.theblock.co", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Decrypt", "feed_url": "https://decrypt.co/feed", "site_url": "https://decrypt.co", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "CryptoSlate", "feed_url": "https://cryptoslate.com/feed/", "site_url": "https://cryptoslate.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Bitcoinist", "feed_url": "https://bitcoinist.com/feed/", "site_url": "https://bitcoinist.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "NewsBTC", "feed_url": "https://www.newsbtc.com/feed/", "site_url": "https://www.newsbtc.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Bitcoin Times", "feed_url": "https://bitcoinmagazine.com/feed", "site_url": "https://bitcoinmagazine.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Crypto Briefing", "feed_url": "https://cryptobriefing.com/feed/", "site_url": "https://cryptobriefing.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    {"name": "BeInCrypto", "feed_url": "https://beincrypto.com/feed/", "site_url": "https://beincrypto.com", "category_hint": "crypto", "language": "en", "crawl_difficulty": "easy"},
    
    # Major Finance/Business
    {"name": "Reuters Business", "feed_url": "https://feeds.reuters.com/reuters/businessNews", "site_url": "https://www.reuters.com", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Bloomberg Markets", "feed_url": "https://feeds.bloomberg.com/markets/news.rss", "site_url": "https://www.bloomberg.com", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "CNBC", "feed_url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "site_url": "https://www.cnbc.com", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Financial Times", "feed_url": "https://www.ft.com/?format=rss", "site_url": "https://www.ft.com", "category_hint": "finance", "language": "en", "crawl_difficulty": "medium"},
    {"name": "MarketWatch", "feed_url": "https://feeds.marketwatch.com/marketwatch/topstories/", "site_url": "https://www.marketwatch.com", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Yahoo Finance", "feed_url": "https://finance.yahoo.com/news/rssindex", "site_url": "https://finance.yahoo.com", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Investopedia", "feed_url": "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline", "site_url": "https://www.investopedia.com", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    
    # Major World News
    {"name": "BBC News", "feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml", "site_url": "https://www.bbc.com/news/world", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    {"name": "BBC Business", "feed_url": "https://feeds.bbci.co.uk/news/business/rss.xml", "site_url": "https://www.bbc.com/news/business", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "CNN", "feed_url": "http://rss.cnn.com/rss/edition.rss", "site_url": "https://www.cnn.com", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Guardian World", "feed_url": "https://www.theguardian.com/world/rss", "site_url": "https://www.theguardian.com/world", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Guardian Business", "feed_url": "https://www.theguardian.com/business/rss", "site_url": "https://www.theguardian.com/business", "category_hint": "finance", "language": "en", "crawl_difficulty": "easy"},
    {"name": "NPR", "feed_url": "https://feeds.npr.org/1001/rss.xml", "site_url": "https://www.npr.org", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Al Jazeera", "feed_url": "https://www.aljazeera.com/xml/rss/all.xml", "site_url": "https://www.aljazeera.com", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    {"name": "AP News", "feed_url": "https://rsshub.app/apnews/topnews", "site_url": "https://apnews.com", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    
    # Asia Pacific
    {"name": "South China Morning Post", "feed_url": "https://www.scmp.com/rss/91/feed", "site_url": "https://www.scmp.com", "category_hint": "asia", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Nikkei Asia", "feed_url": "https://asia.nikkei.com/rss/ndn", "site_url": "https://asia.nikkei.com", "category_hint": "asia", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Channel News Asia", "feed_url": "https://www.channelnewsasia.com/rss/latest", "site_url": "https://www.channelnewsasia.com", "category_hint": "asia", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Straits Times", "feed_url": "https://www.straitstimes.com/news/world/rss.xml", "site_url": "https://www.straitstimes.com", "category_hint": "asia", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Bangkok Post", "feed_url": "https://www.bangkokpost.com/rss/feed/?path=news/world", "site_url": "https://www.bangkokpost.com", "category_hint": "asia", "language": "en", "crawl_difficulty": "easy"},
    {"name": "ABS-CBN News", "feed_url": "https://news.abs-cbn.com/feed/world", "site_url": "https://news.abs-cbn.com", "category_hint": "asia", "language": "en", "crawl_difficulty": "medium"},
    
    # Vietnam
    {"name": "VnExpress", "feed_url": "https://vnexpress.net/rss/the-gioi.rss", "site_url": "https://vnexpress.net", "category_hint": "vietnam", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "Tuoi Tre", "feed_url": "https://tuoitre.vn/rss/the-gioi.rss", "site_url": "https://tuoitre.vn", "category_hint": "vietnam", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "Thanh Nien", "feed_url": "https://thanhnien.vn/rss/the-gioi.rss", "site_url": "https://thanhnien.vn", "category_hint": "vietnam", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "VietnamNet", "feed_url": "https://vietnamnet.vn/rss/the-gioi.rss", "site_url": "https://vietnamnet.vn", "category_hint": "vietnam", "language": "vi", "crawl_difficulty": "easy"},
    {"name": "Nhan Dan", "feed_url": "https://nhandan.vn/rss/the-gioi.rss", "site_url": "https://nhandan.vn", "category_hint": "vietnam", "language": "vi", "crawl_difficulty": "easy"},
    
    # Europe
    {"name": "Euronews", "feed_url": "https://www.euronews.com/rss", "site_url": "https://www.euronews.com", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Local Europe", "feed_url": "https://www.thelocal.com/feed/", "site_url": "https://www.thelocal.com", "category_hint": "europe", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Politico Europe", "feed_url": "https://www.politico.eu/feed/", "site_url": "https://www.politico.eu", "category_hint": "politics", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Deutsche Welle", "feed_url": "https://rss.dw.com/rdf/rss-en-all", "site_url": "https://www.dw.com", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    {"name": "France24", "feed_url": "https://www.france24.com/en/rss", "site_url": "https://www.france24.com", "category_hint": "world", "language": "en", "crawl_difficulty": "easy"},
    
    # Tech News
    {"name": "TechCrunch", "feed_url": "https://techcrunch.com/feed/", "site_url": "https://techcrunch.com", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "The Verge", "feed_url": "https://www.theverge.com/rss/index.xml", "site_url": "https://www.theverge.com", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Wired", "feed_url": "https://www.wired.com/feed/rss", "site_url": "https://www.wired.com", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Ars Technica", "feed_url": "https://feeds.arstechnica.com/arstechnica/index", "site_url": "https://arstechnica.com", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "MIT Technology Review", "feed_url": "https://www.technologyreview.com/feed/", "site_url": "https://www.technologyreview.com", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Engadget", "feed_url": "https://www.engadget.com/rss.xml", "site_url": "https://www.engadget.com", "category_hint": "tech", "language": "en", "crawl_difficulty": "easy"},
    
    # Markets/Stocks
    {"name": "Trading Economics", "feed_url": "https://tradingeconomics.com/rss/news.ashx", "site_url": "https://tradingeconomics.com", "category_hint": "markets", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Seeking Alpha", "feed_url": "https://seekingalpha.com/feed.xml", "site_url": "https://seekingalpha.com", "category_hint": "markets", "language": "en", "crawl_difficulty": "medium"},
    {"name": "Barron's", "feed_url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "site_url": "https://www.barrons.com", "category_hint": "markets", "language": "en", "crawl_difficulty": "easy"},
    {"name": "Investing.com", "feed_url": "https://www.investing.com/rss/news.rss", "site_url": "https://www.investing.com", "category_hint": "markets", "language": "en", "crawl_difficulty": "easy"},
    
    # Latin America
    {"name": "La Nacion", "feed_url": "https://www.lanacion.com.ar/rss/urgentes.xml", "site_url": "https://www.lanacion.com.ar", "category_hint": "latam", "language": "es", "crawl_difficulty": "medium"},
    {"name": "El Tiempo", "feed_url": "https://www.eltiempo.com/rss/investigacion.xml", "site_url": "https://www.eltiempo.com", "category_hint": "latam", "language": "es", "crawl_difficulty": "medium"},
    {"name": "Folha de S.Paulo", "feed_url": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml", "site_url": "https://www.folha.uol.com.br", "category_hint": "latam", "language": "pt", "crawl_difficulty": "medium"},
    
    # Middle East
    {"name": "RT Arabic", "feed_url": "https://arabic.rt.com/rss/", "site_url": "https://arabic.rt.com", "category_hint": "middle_east", "language": "ar", "crawl_difficulty": "easy"},
    {"name": "The National UAE", "feed_url": "https://www.thenationalnews.com/uae/rss/", "site_url": "https://www.thenationalnews.com", "category_hint": "middle_east", "language": "en", "crawl_difficulty": "easy"},
    
    # Africa
    {"name": "Mail & Guardian", "feed_url": "https://mg.co.za/feed/", "site_url": "https://mg.co.za", "category_hint": "africa", "language": "en", "crawl_difficulty": "easy"},
    {"name": "AllAfrica", "feed_url": "https://allafrica.com/tools/headlines/rdf/fullstory.rdf", "site_url": "https://allafrica.com", "category_hint": "africa", "language": "en", "crawl_difficulty": "easy"},
]


async def seed_sources():
    """Insert all sources into the database."""
    async with async_session_maker() as session:
        added_count = 0
        for source in SOURCES:
            try:
                # Check if feed_url already exists
                result = await session.execute(
                    text("SELECT id FROM sources WHERE feed_url = :feed_url"),
                    {"feed_url": source["feed_url"]}
                )
                existing = result.fetchone()
                
                if existing:
                    print(f"Skipping (exists): {source['name']}")
                    continue
                
                # Insert new source with UUID and timestamps
                await session.execute(
                    text("""
                        INSERT INTO sources (id, name, feed_url, site_url, category_hint, language, is_active, fetch_interval, crawl_difficulty, requires_flaresolverr, requires_proxy, is_paywall, created_at, updated_at)
                        VALUES (gen_random_uuid(), :name, :feed_url, :site_url, :category_hint, :language, true, 15, :crawl_difficulty, false, false, false, NOW(), NOW())
                    """),
                    source
                )
                print(f"Added: {source['name']}")
                added_count += 1
            except Exception as e:
                print(f"Error adding {source['name']}: {e}")
        
        await session.commit()
        print(f"\nDone! Added {added_count} sources. Total in SOURCES: {len(SOURCES)}")


if __name__ == "__main__":
    asyncio.run(seed_sources())
