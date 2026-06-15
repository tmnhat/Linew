"""
VN Stock news fetcher - lấy tin tức chứng khoán Việt Nam từ nhiều nguồn.
Hỗ trợ cafef.vn RSS, stockbiz.vn, và các nguồn khác.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class VNStockNewsFetcher:
    """
    Fetcher cho VN stock news từ nhiều nguồn.
    """
    
    CAFEF_RSS_BASE = "https://cafef.vn/rss/"
    STOCKBIZ_BASE = "https://stockbiz.vn/"
    VIETSTOCK_BASE = "https://vietstock.vn/"
    
    def __init__(self):
        self._symbol_map = self._build_symbol_map()
    
    def _build_symbol_map(self) -> dict[str, str]:
        """
        Build mapping từ stock code sang tên công ty.
        """
        return {
            "FPT": "FPT Corporation",
            "VNM": "Vietnam Dairy Products JSC",
            "HPG": "Hoà Phát Group",
            "TCB": "Techcombank",
            "MBB": "MB Bank",
            "CTG": "VietinBank",
            "BID": "BIDV",
            "VIC": "Vingroup",
            "VHM": "Vinhomes",
            "MSN": "Masan Group",
            "SSI": "SSI Securities",
            "GAS": "Petrovietnam Gas",
            "PLX": "Petrolimex",
            "STB": "Sacombank",
            "ACB": "ACB",
            "REE": "REE Corporation",
            "MWG": "Mobile World Group",
            "PNJ": "Phu Nhuan Jewelry",
            "VRE": "Vincom Retail",
            "VND": "VNDirect Securities",
            "HDB": "HDBank",
            "TPB": "TPBank",
            "VPB": "VPBank",
            "SHB": "SHBank",
            "EIB": "Eximbank",
            "OCB": "OCB Bank",
            "BCM": "Becamex IDC",
            "BVH": "Bao Viet Holdings",
            "KDH": "Khang Dien House",
            "NLG": "Nam Long Group",
            "NT2": "NT2 Power",
            "PVD": "Petrovietnam Drilling",
            "PVS": "Petrovietnam Services",
            "VPI": "Vinpearl",
            "VSH": "Vien Sinai",
            "AAA": "An Giang Agriculture",
            "ACC": "ACC Concrete",
            "ACL": "ACL Commerce",
            "ASM": "Sa Giang",
            "BMP": "Binh Minh Plastics",
            "CLC": "Cam Pha Cement",
            "CMG": "CMG Services",
            "CNG": "CNG Vietnam",
            "DBC": "Dabaco Group",
            "DGC": "Duc Giang Chemicals",
            "DHG": "DHG Pharmaceutical",
            "DPM": "Petrovietnam Fertilizer",
            "DRC": "Duc Cuong Land",
            "HSG": "Hoang Son",
            "HAG": "Hoang Anh Gia Lai",
            "KDC": "Kido Group",
            "KHL": "Khaisan",
            "LAF": "Lao Cai Fertilizer",
            "LDG": "LDG Investment",
            "MSH": "Mai Son",
            "NSC": "National Seed",
            "OGC": "Ocean Group",
            "PPC": "Petrovietnam Power",
            "SCR": "Sacomreal",
            "SJS": "Dat Phuong Group",
            "SMA": "Saigon Minerals",
            "STT": "Saigon Thuong Tin",
            "TNA": "Thien Nam Trading",
            "TRA": "Traphaco",
            "TSC": "Tay Bac Securities",
            "VCB": "Vietcombank",
            "VCG": "Vietcapital Bank",
        }
    
    def get_company_name(self, symbol: str) -> str:
        """Get company name từ symbol."""
        return self._symbol_map.get(symbol.upper(), symbol)
    
    async def fetch_cafef_rss(self, symbol: str, limit: int = 10) -> list[dict]:
        """
        Lấy tin tức từ cafef.vn RSS feed.
        
        Args:
            symbol: Stock symbol (VD: "FPT", "VNM")
            limit: Số lượng tin tối đa
            
        Returns:
            List of news items
        """
        news = []
        
        try:
            # cafef RSS format: https://cafef.vn/rss/{symbol}.rss
            url = f"{self.CAFEF_RSS_BASE}{symbol.lower()}.rss"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    
                    for entry in feed.entries[:limit]:
                        news.append({
                            "title": entry.get("title", ""),
                            "summary": entry.get("summary", "")[:300],
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "source": "cafef.vn",
                        })
                else:
                    logger.warning(f"cafef RSS error for {symbol}: {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Failed to fetch cafef RSS for {symbol}: {e}")
        
        return news
    
    async def fetch_vietstock_news(self, symbol: str, limit: int = 10) -> list[dict]:
        """
        Lấy tin tức từ vietstock.vn.
        """
        news = []
        
        try:
            # Vietstock news URL pattern
            url = f"{self.VIETSTOCK_BASE}{symbol}/tin-tuc/"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Set headers để bypass some restrictions
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Find news items - CSS selectors có thể thay đổi
                    articles = soup.select("div.news-listing h3 a, div.article-item h3 a, .list-news h3 a")
                    
                    for article in articles[:limit]:
                        title = article.get_text(strip=True)
                        link = article.get("href", "")
                        
                        if title and link:
                            news.append({
                                "title": title,
                                "summary": "",
                                "link": link if link.startswith("http") else f"{self.VIETSTOCK_BASE}{link}",
                                "source": "vietstock.vn",
                            })
                else:
                    logger.warning(f"vietstock news error for {symbol}: {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Failed to fetch vietstock news for {symbol}: {e}")
        
        return news
    
    async def fetch_stockbiz_news(self, symbol: str, limit: int = 5) -> list[dict]:
        """
        Lấy tin tức từ stockbiz.vn.
        """
        news = []
        
        try:
            url = f"{self.STOCKBIZ_BASE}{symbol}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    articles = soup.select("div.news-item h4 a, .tintuc-item h3 a")
                    
                    for article in articles[:limit]:
                        title = article.get_text(strip=True)
                        link = article.get("href", "")
                        
                        if title:
                            news.append({
                                "title": title,
                                "summary": "",
                                "link": link if link.startswith("http") else f"{self.STOCKBIZ_BASE}{link}",
                                "source": "stockbiz.vn",
                            })
                            
        except Exception as e:
            logger.warning(f"Failed to fetch stockbiz news for {symbol}: {e}")
        
        return news
    
    async def get_stock_news(self, symbol: str, limit: int = 10) -> list[str]:
        """
        Lấy tất cả news headlines cho một cổ phiếu VN.
        Kết hợp từ nhiều nguồn.
        
        Args:
            symbol: Stock symbol (VD: "FPT", "VNM")
            limit: Số lượng headlines tối đa
            
        Returns:
            List of news headlines
        """
        all_news = []
        symbol_upper = symbol.upper()
        
        # Fetch from multiple sources in parallel
        tasks = [
            self.fetch_cafef_rss(symbol_upper, limit),
            self.fetch_vietstock_news(symbol_upper, limit),
            self.fetch_stockbiz_news(symbol_upper, limit),
        ]
        
        import asyncio
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                for item in result:
                    title = item.get("title", "")
                    if title and title not in all_news:
                        all_news.append(title)
        
        return all_news[:limit]
    
    async def get_market_news(self, limit: int = 20) -> list[dict]:
        """
        Lấy tin tức thị trường chung (VN-Index, thị trường).
        """
        market_news = []
        
        # VN-Index market news from cafef
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.CAFEF_RSS_BASE}vnindex.rss")
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    
                    for entry in feed.entries[:limit]:
                        market_news.append({
                            "title": entry.get("title", ""),
                            "summary": entry.get("summary", "")[:300],
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "source": "cafef.vn",
                            "category": "market",
                        })
                        
        except Exception as e:
            logger.warning(f"Failed to fetch market news: {e}")
        
        # Thị trường chứng khoán RSS
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.CAFEF_RSS_BASE}thitruong.rss")
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    
                    for entry in feed.entries[:limit]:
                        market_news.append({
                            "title": entry.get("title", ""),
                            "summary": entry.get("summary", "")[:300],
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "source": "cafef.vn",
                            "category": "market",
                        })
                        
        except Exception as e:
            logger.warning(f"Failed to fetch market RSS: {e}")
        
        # Remove duplicates
        seen_titles = set()
        unique_news = []
        for item in market_news:
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                unique_news.append(item)
        
        return unique_news[:limit]
    
    async def get_sector_news(self, sector: str, limit: int = 10) -> list[dict]:
        """
        Lấy tin tức theo ngành.
        
        Args:
            sector: Tên ngành (VD: "banking", "real-estate", "retail")
            limit: Số lượng tin tối đa
        """
        sector_map = {
            "banking": "nganhang",
            "real-estate": "batdongsan",
            "retail": "banle",
            "technology": "cntt",
            "energy": "dien-luc",
            "construction": "xaydung",
            "food": "thucpham",
            "pharma": "duocpham",
        }
        
        category = sector_map.get(sector.lower(), sector.lower())
        news = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.CAFEF_RSS_BASE}{category}.rss")
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    
                    for entry in feed.entries[:limit]:
                        news.append({
                            "title": entry.get("title", ""),
                            "summary": entry.get("summary", "")[:300],
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "source": "cafef.vn",
                            "sector": sector,
                        })
                        
        except Exception as e:
            logger.warning(f"Failed to fetch sector news for {sector}: {e}")
        
        return news


# Singleton instance
vn_stock_news_fetcher = VNStockNewsFetcher()


async def fetch_vn_stock_news(symbol: str, limit: int = 10) -> list[str]:
    """
    Helper function để fetch news cho một cổ phiếu VN.
    
    Args:
        symbol: Stock symbol (VD: "FPT", "VNM")
        limit: Số lượng headlines
        
    Returns:
        List of news headlines
    """
    return await vn_stock_news_fetcher.get_stock_news(symbol.upper(), limit)


async def fetch_vn_market_news(limit: int = 20) -> list[dict]:
    """
    Helper function để fetch market news.
    """
    return await vn_stock_news_fetcher.get_market_news(limit)
