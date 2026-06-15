"""
Symbol search — autocomplete for widget.
Search in tracked_symbols + symbol_search_cache + Binance.
"""
import logging
from typing import Optional

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.models.tracked_symbols import TrackedSymbol, SymbolSearchCache
from app.prediction.vn_stocks import get_all_vn_stocks, get_default_vn_stocks
from app.prediction.binance_client import binance_client

logger = logging.getLogger(__name__)

# Default symbols to seed - VN stocks only (no US stocks)
DEFAULT_SYMBOLS = [
    # === VN Stock Defaults ===
    *get_default_vn_stocks(),
]

# Crypto - keep for now but can be hidden
CRYPTO_SYMBOLS = [
    {"symbol": "BTC-USD", "name": "Bitcoin", "market": "crypto", "currency": "USD", "is_default": False},
    {"symbol": "ETH-USD", "name": "Ethereum", "market": "crypto", "currency": "USD", "is_default": False},
    {"symbol": "SOL-USD", "name": "Solana", "market": "crypto", "currency": "USD", "is_default": False},
    {"symbol": "BNB-USD", "name": "BNB", "market": "crypto", "currency": "USD", "is_default": False},
    {"symbol": "XRP-USD", "name": "XRP", "market": "crypto", "currency": "USD", "is_default": False},
    {"symbol": "ADA-USD", "name": "Cardano", "market": "crypto", "currency": "USD", "is_default": False},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "market": "crypto", "currency": "USD", "is_default": False},
    {"symbol": "DOT-USD", "name": "Polkadot", "market": "crypto", "currency": "USD", "is_default": False},
]


async def search_symbols(
    query: str,
    market: str = None,
    limit: int = 10,
    db: AsyncSession = None
) -> list[dict]:
    """
    Search symbols by keyword.
    query: "FPT", "bitcoin", "apple", "VNM"...
    market: "crypto", "vn", "us", None (all)
    """
    query_lower = query.lower().strip()
    
    # Use provided session or create new one
    if db is None:
        async with get_db_context() as db:
            return await _search_in_db(db, query_lower, market, limit)
    else:
        return await _search_in_db(db, query_lower, market, limit)


async def _search_in_db(
    db: AsyncSession,
    query_lower: str,
    market: str,
    limit: int
) -> list[dict]:
    """Internal search in database."""
    
    # Build filters
    filters = []
    
    if market:
        filters.append(SymbolSearchCache.market == market)
    
    # Search by symbol or name (case-insensitive) - simplified
    filters.append(
        or_(
            func.lower(SymbolSearchCache.symbol).like(f"{query_lower}%"),
            func.lower(SymbolSearchCache.name).like(f"%{query_lower}%"),
        )
    )
    
    # Check if exact symbol match
    exact_match = await db.execute(
        select(SymbolSearchCache).where(
            func.lower(SymbolSearchCache.symbol) == query_lower
        )
    )
    exact = exact_match.scalars().first()
    
    # Main search query
    stmt = (
        select(SymbolSearchCache)
        .where(*filters)
        .order_by(
            # Exact symbol match first
            func.lower(SymbolSearchCache.symbol) == query_lower,
            # Then symbols starting with query
            func.lower(SymbolSearchCache.symbol).like(f"{query_lower}%"),
            # Then by name match
            func.lower(SymbolSearchCache.name),
        )
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    results = result.scalars().all()
    
    # Build response
    items = []
    seen = set()
    
    # Add exact match first
    if exact and exact.symbol not in seen:
        items.append({
            "symbol": exact.symbol,
            "name": exact.name,
            "market": exact.market,
            "exchange": exact.exchange,
            "currency": exact.currency,
        })
        seen.add(exact.symbol)
    
    # Add search results
    for r in results:
        if r.symbol not in seen:
            items.append({
                "symbol": r.symbol,
                "name": r.name,
                "market": r.market,
                "exchange": r.exchange,
                "currency": r.currency,
            })
            seen.add(r.symbol)
        
        if len(items) >= limit:
            break
    
    return items


async def get_default_symbols(db: AsyncSession = None) -> list[dict]:
    """Get default symbols for widget quick picks."""
    if db is None:
        async with get_db_context() as db:
            return await _get_defaults(db)
    else:
        return await _get_defaults(db)


async def _get_defaults(db: AsyncSession) -> list[dict]:
    """Internal get defaults."""
    stmt = (
        select(TrackedSymbol)
        .where(TrackedSymbol.is_default == True)
        .where(TrackedSymbol.is_active == True)
        .order_by(TrackedSymbol.popularity.desc())
        .limit(8)
    )
    result = await db.execute(stmt)
    symbols = result.scalars().all()
    
    return [{
        "symbol": s.symbol,
        "name": s.name,
        "market": s.market,
        "exchange": s.exchange,
        "currency": s.currency,
        "popularity": s.popularity,
    } for s in symbols]


async def get_popular_symbols(limit: int = 10, db: AsyncSession = None) -> list[dict]:
    """Get popular symbols by popularity score."""
    if db is None:
        async with get_db_context() as db:
            return await _get_popular(db, limit)
    else:
        return await _get_popular(db, limit)


async def _get_popular(db: AsyncSession, limit: int) -> list[dict]:
    """Internal get popular."""
    stmt = (
        select(TrackedSymbol)
        .where(TrackedSymbol.is_active == True)
        .order_by(TrackedSymbol.popularity.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    symbols = result.scalars().all()
    
    return [{
        "symbol": s.symbol,
        "name": s.name,
        "market": s.market,
        "exchange": s.exchange,
        "currency": s.currency,
        "popularity": s.popularity,
    } for s in symbols]


async def get_tracked_symbol(symbol: str, market: str = None, db: AsyncSession = None) -> Optional[dict]:
    """Get tracked symbol info."""
    if db is None:
        async with get_db_context() as db:
            return await _get_tracked(db, symbol, market)
    else:
        return await _get_tracked(db, symbol, market)


async def _get_tracked(db: AsyncSession, symbol: str, market: str) -> Optional[dict]:
    """Internal get tracked symbol."""
    filters = [func.lower(TrackedSymbol.symbol) == symbol.lower()]
    if market:
        filters.append(TrackedSymbol.market == market)
    
    stmt = select(TrackedSymbol).where(*filters)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    
    return s.to_dict() if s else None


async def upsert_tracked_symbol(
    symbol: str,
    name: str,
    market: str,
    exchange: str = None,
    currency: str = "USD",
    is_default: bool = False,
    db: AsyncSession = None
) -> dict:
    """Insert or update tracked symbol."""
    if db is None:
        async with get_db_context() as db:
            return await _upsert_tracked(db, symbol, name, market, exchange, currency, is_default)
    else:
        return await _upsert_tracked(db, symbol, name, market, exchange, currency, is_default)


async def _upsert_tracked(
    db: AsyncSession,
    symbol: str,
    name: str,
    market: str,
    exchange: str,
    currency: str,
    is_default: bool
) -> dict:
    """Internal upsert."""
    from sqlalchemy.dialects.postgresql import insert
    from datetime import datetime
    
    stmt = insert(TrackedSymbol).values(
        symbol=symbol.upper(),
        name=name,
        market=market,
        exchange=exchange,
        currency=currency,
        is_default=is_default,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "market"],
        set_={
            "name": stmt.excluded.name,
            "exchange": stmt.excluded.exchange,
            "currency": stmt.excluded.currency,
        }
    )
    await db.execute(stmt)
    await db.commit()
    
    return await _get_tracked(db, symbol, market)


async def increment_popularity(symbol: str, market: str = None, db: AsyncSession = None) -> bool:
    """Increment popularity score for a symbol."""
    try:
        if db is None:
            async with get_db_context() as db:
                return await _increment_pop(db, symbol, market)
        else:
            return await _increment_pop(db, symbol, market)
    except Exception as e:
        logger.warning(f"Failed to increment popularity for {symbol}: {e}")
        return False


async def _increment_pop(db: AsyncSession, symbol: str, market: str) -> bool:
    """Internal increment."""
    from sqlalchemy import update
    
    filters = [func.lower(TrackedSymbol.symbol) == symbol.lower()]
    if market:
        filters.append(TrackedSymbol.market == market)
    
    stmt = (
        update(TrackedSymbol)
        .where(*filters)
        .values(popularity=TrackedSymbol.popularity + 1)
    )
    await db.execute(stmt)
    await db.commit()
    return True


async def populate_search_cache(db: AsyncSession = None) -> int:
    """
    Populate search cache with default symbols.
    Run once on setup + weekly refresh.
    """
    count = 0
    
    if db is None:
        async with get_db_context() as db:
            return await _populate_cache(db)
    else:
        return await _populate_cache(db)


async def _populate_cache(db: AsyncSession) -> int:
    """Internal populate cache."""
    from sqlalchemy.dialects.postgresql import insert
    
    count = 0
    
    for sym_data in DEFAULT_SYMBOLS:
        try:
            search_text = f"{sym_data['symbol'].lower()} {sym_data['name'].lower()}"
            
            # Upsert to search cache (without search_text to avoid conflict)
            stmt = insert(SymbolSearchCache).values(
                symbol=sym_data['symbol'],
                name=sym_data['name'],
                market=sym_data['market'],
                exchange=sym_data.get('exchange'),
                currency=sym_data.get('currency', 'USD'),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "market"],
                set_={
                    "name": stmt.excluded.name,
                    "exchange": stmt.excluded.exchange,
                    "currency": stmt.excluded.currency,
                }
            )
            await db.execute(stmt)
            
            # Also upsert to tracked symbols
            await _upsert_tracked(
                db,
                sym_data['symbol'],
                sym_data['name'],
                sym_data['market'],
                sym_data.get('exchange'),
                sym_data.get('currency', 'USD'),
                sym_data.get('is_default', False),
            )
            
            count += 1
        except Exception as e:
            logger.warning(f"Failed to cache {sym_data['symbol']}: {e}")
    
    await db.commit()
    logger.info(f"Cached {count} symbols in search cache")
    return count


async def seed_all_symbols(db: AsyncSession = None) -> dict:
    """
    Seed all VN stocks to both tables.
    Returns summary of seeded data.
    """
    from app.prediction.vn_stocks import get_all_vn_stocks, get_default_vn_stocks
    from sqlalchemy.dialects.postgresql import insert
    
    all_vn_stocks = get_all_vn_stocks()
    default_symbols = {s["symbol"] for s in get_default_vn_stocks()}
    count = 0
    count_by_market = {"crypto": 0, "vn": 0, "us": 0}
    
    for sym_data in all_vn_stocks:
        try:
            is_default = sym_data.get("is_default", sym_data["symbol"] in default_symbols)
            
            # Upsert to tracked_symbols
            stmt = insert(TrackedSymbol).values(
                symbol=sym_data['symbol'],
                name=sym_data['name'],
                market=sym_data['market'],
                exchange=sym_data.get('exchange'),
                currency=sym_data.get('currency', 'VND'),
                is_default=is_default,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "market"],
                set_={
                    "name": stmt.excluded.name,
                    "exchange": stmt.excluded.exchange,
                    "currency": stmt.excluded.currency,
                    "is_default": stmt.excluded.is_default,
                }
            )
            await db.execute(stmt)
            
            # Upsert to search cache
            cache_stmt = insert(SymbolSearchCache).values(
                symbol=sym_data['symbol'],
                name=sym_data['name'],
                market=sym_data['market'],
                exchange=sym_data.get('exchange'),
                currency=sym_data.get('currency', 'VND'),
            )
            cache_stmt = cache_stmt.on_conflict_do_update(
                index_elements=["symbol", "market"],
                set_={
                    "name": cache_stmt.excluded.name,
                    "exchange": cache_stmt.excluded.exchange,
                    "currency": cache_stmt.excluded.currency,
                }
            )
            await db.execute(cache_stmt)
            
            count += 1
            count_by_market[sym_data['market']] = count_by_market.get(sym_data['market'], 0) + 1
            
        except Exception as e:
            logger.warning(f"Failed to seed {sym_data['symbol']}: {e}")
    
    await db.commit()
    logger.info(f"Seeded {count} symbols: {count_by_market}")
    
    return {
        "total_seeded": count,
        "by_market": count_by_market,
        "defaults": len(default_symbols),
    }


# ============================================
# BINANCE SEARCH (NEW)
# ============================================

async def search_binance_symbols(query: str, limit: int = 20) -> list[dict]:
    """
    Search Binance symbols by query.
    
    Args:
        query: Search query (e.g., "BTC", "ETH", "SOL")
        limit: Maximum results
        
    Returns:
        List of matching symbols with info
    """
    try:
        # Search from Binance
        binance_results = await binance_client.search_symbols(query.upper(), limit)
        
        results = []
        for item in binance_results:
            # Get 24h ticker for additional info
            ticker = await binance_client.get_24hr_ticker(item["symbol"])
            
            result = {
                "symbol": item["symbol"],
                "name": item["baseAsset"],
                "market": "crypto",
                "exchange": "Binance",
                "currency": item["quoteAsset"],
            }
            
            if ticker:
                result["price"] = ticker.get("last_price")
                result["change_24h"] = ticker.get("price_change_pct")
            
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.warning(f"Failed to search Binance symbols: {e}")
        return []


async def get_binance_trending(limit: int = 10) -> list[dict]:
    """
    Get trending Binance symbols by volume.
    
    Args:
        limit: Number of results
        
    Returns:
        List of trending symbols
    """
    try:
        # Get all USDT symbols (limited for performance)
        all_symbols = await binance_client.get_all_usdt_symbols()
        
        if not all_symbols:
            return []
        
        # Sample top symbols by market cap (well-known ones first)
        top_symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
            "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT", "XLMUSDT"
        ]
        
        trending = []
        for symbol in top_symbols[:limit]:
            ticker = await binance_client.get_24hr_ticker(symbol)
            if ticker:
                trending.append({
                    "symbol": symbol,
                    "name": symbol.replace("USDT", ""),
                    "market": "crypto",
                    "exchange": "Binance",
                    "currency": "USDT",
                    "price": ticker.get("last_price"),
                    "change_24h": ticker.get("price_change_pct"),
                    "volume_24h": ticker.get("quote_volume"),
                })
        
        # Sort by volume
        trending.sort(key=lambda x: x.get("volume_24h", 0) or 0, reverse=True)
        
        return trending[:limit]
        
    except Exception as e:
        logger.warning(f"Failed to get Binance trending: {e}")
        return []
