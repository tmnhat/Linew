"""
Prediction API routes — enhanced with search, popular, track endpoints.
"""
import logging
import random
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.prediction import Prediction
from app.models.prediction_models import TechnicalIndicator, MarketResearch, PredictionFinal
from app.models.price_history import PriceHistory
from app.prediction.data_fetcher import (
    get_price_history, get_latest_price, fetch_current_price,
    fetch_fear_greed, get_fear_greed_data, detect_market_async,
    fetch_vn_history
)
from app.prediction.indicators import calculate_all_indicators
from app.prediction.config import DEFAULT_SYMBOLS, PREDICTION_HORIZONS
from app.prediction.accuracy_tracker import get_accuracy_stats, get_recent_predictions
from app.prediction.alert_monitor import get_active_alerts, create_alert
from app.prediction.symbol_search import (
    search_symbols, get_default_symbols, get_popular_symbols,
    get_tracked_symbol, increment_popularity, seed_all_symbols
)
from app.prediction.cache import (
    get_cached_analysis, cache_analysis, get_cached_indicators, cache_indicators,
    get_cached_news, cache_news, prediction_cache
)
from app.prediction.crypto_news import fetch_crypto_news, get_coin_sentiment
from app.prediction.vn_news import fetch_vn_stock_news

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/prediction", tags=["prediction"])


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    type: str


class PredictionResponse(BaseModel):
    symbol: str
    symbol_name: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    currency: str = "USD"
    currency_symbol: str = "$"
    current_price: Optional[float] = None
    predictions: dict = {}
    indicators: Optional[dict] = None
    analysis: Optional[dict] = None
    accuracy: Optional[dict] = None
    chart_data: Optional[dict] = None
    last_updated: Optional[str] = None
    error: Optional[str] = None


class PredictionDetail(BaseModel):
    horizon: int
    predicted_price: float
    predicted_low: Optional[float] = None
    predicted_high: Optional[float] = None
    change_pct: Optional[float] = None
    confidence_score: Optional[float] = None
    ai_sentiment: Optional[str] = None
    ai_sentiment_score: Optional[float] = None


# ============================================
# SEARCH & POPULAR ENDPOINTS
# ============================================

@router.get("/search")
async def search_symbols_api(
    q: str = Query(..., min_length=1, max_length=50),
    market: Optional[str] = Query(None, regex="^(crypto|vn)$"),  # No US stocks
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Search symbols for autocomplete.
    GET /api/prediction/search?q=FPT&market=vn
    GET /api/prediction/search?q=bitcoin
    """
    try:
        results = await search_symbols(q, market=market, limit=limit, db=db)
        return {"results": results, "query": q, "count": len(results)}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular")
async def popular_symbols(
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Get popular and default symbols for widget quick picks.
    """
    try:
        defaults = await get_default_symbols(db=db)
        popular = await get_popular_symbols(limit=limit, db=db)
        
        return {
            "defaults": defaults,
            "popular": popular,
            "markets": [
                {"key": "crypto", "label": "Crypto", "icon": "₿"},
                {"key": "vn", "label": "VN Stock", "icon": "📈"},
            ]
        }
    except Exception as e:
        logger.error(f"Popular symbols failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track/{symbol}")
async def track_symbol(
    symbol: str,
    market: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Track a symbol (increment popularity).
    GET /api/prediction/track/FPT?market=vn
    """
    try:
        # Auto-detect market if not provided
        if not market:
            market = await detect_market_async(symbol)
        
        # Increment popularity
        await increment_popularity(symbol, market=market, db=db)
        
        # Get symbol info
        sym_info = await get_tracked_symbol(symbol, market=market, db=db)
        
        return {
            "symbol": symbol.upper(),
            "market": market,
            "tracked": True,
            "info": sym_info,
        }
    except Exception as e:
        logger.error(f"Track symbol failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed")
async def seed_symbols(db: AsyncSession = Depends(get_db)):
    """Seed default symbols to database."""
    try:
        result = await seed_all_symbols(db=db)
        return {"message": "Seeded symbols successfully", **result}
    except Exception as e:
        logger.error(f"Seed symbols failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# AI ON-DEMAND ENDPOINT (NEW)
# ============================================

@router.get("/{symbol}/analyze")
async def analyze_on_demand(
    symbol: str,
    force_refresh: bool = Query(False, description="Force refresh AI analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    AI On-Demand Analysis Endpoint.
    
    AI chỉ chạy khi user request widget trên WordPress.
    Kết quả được cache trong Redis để tránh gọi AI liên tục.
    
    GET /api/prediction/{symbol}/analyze
    GET /api/prediction/BTC-USD/analyze
    GET /api/prediction/FPT/analyze?force_refresh=true
    """
    try:
        # Initialize cache
        await prediction_cache.initialize()
        
        symbol_normalized = symbol.upper()
        
        # Skip reserved routes
        if symbol_normalized in ('FEAR-GREED', 'FEAR_GREED', 'SEARCH', 'POPULAR', 'TRACK'):
            raise HTTPException(status_code=404, detail="Invalid symbol")
        
        # Check cache first
        if not force_refresh:
            cached = await get_cached_analysis(symbol_normalized)
            if cached:
                logger.info(f"AI analysis cache hit for {symbol_normalized}")
                return {
                    "source": "cache",
                    "symbol": symbol_normalized,
                    "analysis": cached,
                    "cached_at": cached.get("_cached_at"),
                }
        
        # Detect market
        market = await detect_market_async(symbol_normalized)
        
        # Get symbol info
        sym_info = await get_tracked_symbol(symbol_normalized, market=market, db=db)
        symbol_name = sym_info.get("name") if sym_info else symbol_normalized
        
        # Fetch current price
        price_data = await fetch_current_price(symbol_normalized, market=market)
        current_price = price_data.get("price") if price_data else None
        price_change_pct = price_data.get("change_pct", 0) if price_data else 0
        
        if not current_price:
            raise HTTPException(status_code=400, detail=f"Cannot fetch price for {symbol}")
        
        # Determine currency
        currency = sym_info.get("currency", "USD") if sym_info else ("VND" if market == "vn" else "USD")
        
        # Get price history for indicators
        history = await get_price_history(db, symbol_normalized, days=365)
        
        if len(history) < 30:
            raise HTTPException(status_code=400, detail=f"Not enough price history for {symbol}")
        
        # Calculate technical indicators
        highs = [float(h.get("high", h.get("close", 0))) for h in history if h.get("high") or h.get("close")]
        lows = [float(h.get("low", h.get("close", 0))) for h in history if h.get("low") or h.get("close")]
        closes = [float(h.get("close", 0)) for h in history if h.get("close")]
        volumes = [int(h.get("volume", 0)) for h in history if h.get("volume")]
        
        indicators = calculate_all_indicators(highs, lows, closes, volumes)
        indicators = {k: float(v) if v is not None else None for k, v in indicators.items()}
        
        # Get Fear & Greed (for crypto)
        fear_greed = None
        if market == "crypto":
            fear_greed_data = await fetch_fear_greed()
            fear_greed = fear_greed_data
        
        # Fetch news based on market type
        recent_news = []
        try:
            if market == "crypto":
                recent_news = await fetch_crypto_news(symbol_normalized, limit=10)
            elif market == "vn":
                recent_news = await fetch_vn_stock_news(symbol_normalized, limit=10)
        except Exception as e:
            logger.warning(f"Failed to fetch news for {symbol}: {e}")

        # Call AI analysis (Prediction V2 - Multi-Agent)
        from app.prediction.ai_analyst import analyze_symbol_enhanced
        from app.prediction.ai_analyst import get_latest_analysis
        from app.prediction.fundamental_data import get_fundamental_fetcher
        from app.prediction.macro_data import get_macro_fetcher
        from app.prediction.event_calendar import get_event_calendar

        # Try to get existing analysis first
        existing_analysis = await get_latest_analysis(symbol_normalized)

        # If analysis exists and less than 1 hour old, use it
        if existing_analysis and not force_refresh:
            # Update cache
            existing_analysis["_cached_at"] = datetime.utcnow().isoformat()
            await cache_analysis(symbol_normalized, existing_analysis)

            return {
                "source": "database",
                "symbol": symbol_normalized,
                "analysis": existing_analysis,
            }

        # Fetch additional data for Prediction V2
        fundamentals = None
        macro_data = None
        events = None

        try:
            if market in ("crypto", "us"):
                fetcher = get_fundamental_fetcher()
                fundamentals = await fetcher.get_fundamentals(symbol_normalized, market)

                macro_fetcher = get_macro_fetcher()
                macro_data = await macro_fetcher.get_all_macro_data()

                event_fetcher = get_event_calendar()
                events = await event_fetcher.get_all_events(symbol_normalized)
        except Exception as e:
            logger.warning(f"Failed to fetch additional data for {symbol}: {e}")

        # Run fresh AI analysis (Prediction V2 - Multi-Agent)
        logger.info(f"Running Prediction V2 multi-agent analysis for {symbol_normalized} (market={market})")

        analysis = await analyze_symbol_enhanced(
            symbol=symbol_normalized,
            symbol_name=symbol_name,
            market=market,
            current_price=current_price,
            price_change_pct=price_change_pct,
            indicators=indicators,
            fundamentals=fundamentals,
            macro_data=macro_data,
            events=events,
            fear_greed=fear_greed,
            recent_news=recent_news,
            currency=currency,
        )
        
        if not analysis:
            raise HTTPException(status_code=500, detail="AI analysis failed")
        
        # Add cached timestamp
        analysis["_cached_at"] = datetime.utcnow().isoformat()
        
        # Cache the result
        await cache_analysis(symbol_normalized, analysis)
        
        return {
            "source": "fresh",
            "symbol": symbol_normalized,
            "analysis": analysis,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MAIN PREDICTION ENDPOINT (ENHANCED)
# ============================================

@router.get("/{symbol}", response_model=PredictionResponse)
async def get_prediction(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full prediction for a symbol including:
    - Current price
    - Predictions for all horizons (1d, 7d, 30d)
    - AI analysis with why_moving, risks
    - Accuracy stats
    - Chart data
    """
    try:
        # Normalize symbol
        symbol_normalized = symbol.upper()

        # Skip reserved routes
        if symbol_normalized in ('FEAR-GREED', 'FEAR_GREED', 'SEARCH', 'POPULAR', 'TRACK'):
            raise HTTPException(status_code=404, detail="Invalid symbol")

        # Detect market
        market = await detect_market_async(symbol_normalized)
        
        # Get tracked symbol info
        sym_info = await get_tracked_symbol(symbol_normalized, market=market, db=db)
        
        # Determine currency
        currency = sym_info.get("currency", "USD") if sym_info else ("VND" if market == "vn" else "USD")
        currency_symbol = "₫" if currency == "VND" else "$"
        
        # Fetch current price
        price_data = await fetch_current_price(symbol_normalized, market=market)
        current_price = price_data.get("price") if price_data else None

        # Get predictions from DB
        result = await db.execute(
            select(PredictionFinal)
            .where(func.lower(PredictionFinal.symbol) == symbol_normalized.lower())
            .order_by(desc(PredictionFinal.generated_at))
            .limit(100)
        )
        predictions_final = result.scalars().all()

        predictions_dict = {}
        for pred in predictions_final:
            horizon_key = f"{pred.horizon_days}d"
            if horizon_key not in predictions_dict:
                predictions_dict[horizon_key] = PredictionDetail(
                    horizon=pred.horizon_days,
                    predicted_price=float(pred.predicted_price) if pred.predicted_price else None,
                    predicted_low=float(pred.predicted_low) if pred.predicted_low else None,
                    predicted_high=float(pred.predicted_high) if pred.predicted_high else None,
                    change_pct=float(pred.change_pct) if pred.change_pct else None,
                    confidence_score=float(pred.confidence_score) if pred.confidence_score else None,
                    ai_sentiment=pred.ai_sentiment,
                    ai_sentiment_score=float(pred.ai_sentiment_score) if pred.ai_sentiment_score else None,
                )

        # Auto-fetch price history for VN stocks if missing (BEFORE chart data)
        if market == 'vn' and current_price:
            result = await db.execute(
                select(func.count())
                .select_from(PriceHistory)
                .where(func.lower(PriceHistory.symbol) == symbol_normalized.lower())
            )
            count = result.scalar() or 0
            if count < 30:  # Need at least 30 days for prediction
                try:
                    # Fetch history from vnstock
                    await fetch_vn_history(db, symbol_normalized, period='1y')
                    logger.info(f"Auto-fetched price history for {symbol_normalized}")
                except Exception as e:
                    logger.warning(f"Failed to auto-fetch history for {symbol_normalized}: {e}")

        # Auto-generate mock predictions for VN stocks if missing
        if market == 'vn' and current_price and len(predictions_dict) == 0:
            try:
                await _generate_mock_predictions(db, symbol_normalized, market, current_price)
                # Re-fetch predictions
                result = await db.execute(
                    select(PredictionFinal)
                    .where(func.lower(PredictionFinal.symbol) == symbol_normalized.lower())
                    .order_by(desc(PredictionFinal.generated_at))
                    .limit(100)
                )
                predictions_final = result.scalars().all()
                for pred in predictions_final:
                    horizon_key = f"{pred.horizon_days}d"
                    if horizon_key not in predictions_dict:
                        predictions_dict[horizon_key] = PredictionDetail(
                            horizon=pred.horizon_days,
                            predicted_price=float(pred.predicted_price) if pred.predicted_price else None,
                            predicted_low=float(pred.predicted_low) if pred.predicted_low else None,
                            predicted_high=float(pred.predicted_high) if pred.predicted_high else None,
                            change_pct=float(pred.change_pct) if pred.change_pct else None,
                            confidence_score=float(pred.confidence_score) if pred.confidence_score else None,
                            ai_sentiment=pred.ai_sentiment,
                            ai_sentiment_score=float(pred.ai_sentiment_score) if pred.ai_sentiment_score else None,
                        )
                logger.info(f"Auto-generated mock predictions for {symbol_normalized}")
            except Exception as e:
                logger.warning(f"Failed to auto-generate predictions for {symbol_normalized}: {e}")

        # Get market research
        result = await db.execute(
            select(MarketResearch)
            .where(func.lower(MarketResearch.symbol) == symbol_normalized.lower())
            .order_by(desc(MarketResearch.analysis_date))
            .limit(1)
        )
        research = result.scalar_one_or_none()

        # Get accuracy stats
        accuracy = await get_accuracy_stats(symbol_normalized, days=30)

        # Get chart data (AFTER auto-fetch to ensure data is available)
        history = await get_price_history(db, symbol_normalized, days=90)
        chart_data = _build_chart_data(history, predictions_final)

        # Calculate technical indicators FIRST
        indicators = None
        if len(history) >= 30:
            try:
                highs = [float(h.get("high", h.get("close", 0))) for h in history if h.get("high") or h.get("close")]
                lows = [float(h.get("low", h.get("close", 0))) for h in history if h.get("low") or h.get("close")]
                closes = [float(h.get("close", 0)) for h in history if h.get("close")]
                volumes = [int(h.get("volume", 0)) for h in history if h.get("volume")]
                
                if len(closes) >= 30:
                    indicators = calculate_all_indicators(highs, lows, closes, volumes)
                    # Convert Decimal to float for JSON serialization
                    indicators = {k: float(v) if v is not None else None for k, v in indicators.items()}
            except Exception as e:
                logger.warning(f"Failed to calculate indicators for {symbol}: {e}")

        # Build analysis (AFTER indicators calculation)
        analysis = None
        if research:
            analysis = {
                "sentiment": research.sentiment,
                "sentiment_score": float(research.sentiment_score) if research.sentiment_score else None,
                "analysis_vi": research.analysis_vi,
                "why_moving": research.why_moving or [],
                "risks": research.risks or [],
                "opportunities": research.opportunities or [],
                "key_factors": _extract_key_factors(research),
                "fear_greed_index": research.fear_greed_index,
                "fear_greed_value": research.fear_greed_value,
            }
        elif market == 'vn' and current_price:
            # Generate mock analysis for VN stocks
            analysis = _generate_mock_analysis(
                symbol_normalized, market, current_price, indicators, currency
            )

        last_updated = predictions_final[0].generated_at.isoformat() if predictions_final else None
        
        # Get symbol name
        symbol_name = sym_info.get("name") if sym_info else symbol_normalized

        return PredictionResponse(
            symbol=symbol_normalized,
            symbol_name=symbol_name,
            market=market,
            exchange=sym_info.get("exchange") if sym_info else None,
            currency=currency,
            currency_symbol=currency_symbol,
            current_price=current_price,
            predictions=predictions_dict,
            indicators=indicators,
            analysis=analysis,
            accuracy=accuracy,
            chart_data=chart_data,
            last_updated=last_updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prediction for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_key_factors(research) -> list:
    """Extract key factors from research record."""
    factors = []
    
    # From key_factors JSONB field
    if research.key_factors:
        if isinstance(research.key_factors, list):
            for f in research.key_factors:
                if isinstance(f, dict):
                    factors.append(f.get("factor", str(f)))
                else:
                    factors.append(str(f))
        else:
            factors.append(str(research.key_factors))
    
    return factors[:5]  # Limit to 5 factors


def _build_chart_data(history: list[dict], predictions: list) -> dict:
    """Build chart data from history and predictions."""
    actual_prices = []
    for h in history:
        actual_prices.append({
            "date": h["date"],
            "price": h.get("close"),
        })

    pred_by_date = {}
    for p in predictions:
        key = p.prediction_date.isoformat() if hasattr(p, 'prediction_date') and p.prediction_date else None
        if key:
            if key not in pred_by_date:
                pred_by_date[key] = {}
            horizon_key = f"{p.horizon_days}d"
            pred_by_date[key][horizon_key] = float(p.predicted_price) if p.predicted_price else None

    chart_points = []
    for ap in actual_prices[-30:]:
        date_str = ap["date"]
        point = {
            "date": date_str,
            "actual": ap["price"],
        }
        if date_str in pred_by_date:
            point.update(pred_by_date[date_str])
        chart_points.append(point)

    return {"points": chart_points, "labels": [p["date"] for p in actual_prices[-30:]]}


def _generate_mock_analysis(
    symbol: str,
    market: str,
    current_price: float,
    indicators: Optional[dict],
    currency: str,
) -> dict:
    """
    Generate mock analysis based on technical indicators.
    Used when AI analysis is not available.
    """
    currency_symbol = "₫" if currency == "VND" else "$"
    
    # Determine sentiment based on RSI and price trends
    rsi = indicators.get("rsi_14") if indicators else None
    macd_hist = indicators.get("macd_histogram") if indicators else None
    sma_20 = indicators.get("sma_20") if indicators else None
    sma_50 = indicators.get("sma_50") if indicators else None
    
    sentiment = "neutral"
    sentiment_score = 0.5
    
    if rsi is not None:
        if rsi > 70:
            sentiment = "bearish"
            sentiment_score = 0.75
        elif rsi < 30:
            sentiment = "bullish"
            sentiment_score = 0.75
    
    if macd_hist is not None:
        if macd_hist > 0 and sentiment != "bearish":
            sentiment = "bullish"
            sentiment_score = max(sentiment_score, 0.65)
        elif macd_hist < 0 and sentiment != "bullish":
            sentiment = "bearish"
            sentiment_score = max(sentiment_score, 0.65)
    
    if sma_20 and sma_50 and sma_20 > sma_50 * 1.02:
        sentiment = "bullish"
        sentiment_score = max(sentiment_score, 0.7)
    elif sma_20 and sma_50 and sma_20 < sma_50 * 0.98:
        sentiment = "bearish"
        sentiment_score = max(sentiment_score, 0.7)
    
    # Generate why_moving based on indicators
    why_moving = []
    if rsi is not None:
        if rsi > 65:
            why_moving.append(f"RSI {rsi:.1f} cho thấy đà tăng đang yếu dần, có thể điều chỉnh")
        elif rsi < 45:
            why_moving.append(f"RSI {rsi:.1f} cho thấy áp lực bán đang giảm dần")
    
    if macd_hist is not None:
        if macd_hist > 0:
            why_moving.append("MACD histogram dương, đà tăng đang chiếm ưu thế")
        else:
            why_moving.append("MACD histogram âm, đà giảm đang chiếm ưu thế")
    
    if sma_20 and sma_50:
        if sma_20 > sma_50:
            why_moving.append("SMA 20 > SMA 50: xu hướng ngắn hạn đang tích cực")
        else:
            why_moving.append("SMA 20 < SMA 50: xu hướng ngắn hạn đang tiêu cực")
    
    # Generate risks
    risks = []
    if rsi and rsi > 75:
        risks.append("RSI quá mua cao, nguy cơ điều chỉnh mạnh")
    if rsi and rsi < 25:
        risks.append("RSI quá bán thấp, có thể xuất hiện nhịp hồi kỹ thuật")
    
    if not why_moving:
        why_moving.append("Giá đang trong giai đoạn tích lũy, chưa có xu hướng rõ ràng")
    if not risks:
        risks.append("Thị trường biến động, cần theo dõi sát diễn biến")
    
    # Generate opportunities
    opportunities = []
    if sentiment == "bullish":
        opportunities.append("Xu hướng tăng đang được xác nhận bởi các chỉ báo kỹ thuật")
        opportunities.append("Khuyến nghị theo dõi và mua vào khi có nhịp điều chỉnh")
    elif sentiment == "bearish":
        opportunities.append("Có thể chờ đợi điểm vào tốt hơn ở vùng hỗ trợ")
        opportunities.append("Khuyến nghị quan sát, chưa nên mua mới ở thời điểm hiện tại")
    else:
        opportunities.append("Thị trường đang cân bằng, chờ tín hiệu rõ ràng hơn")
        opportunities.append("Có thể giao dịch trong biên độ hẹp")
    
    # Generate analysis text
    sentiment_text = {
        "bullish": "tích cực",
        "bearish": "tiêu cực",
        "neutral": "trung lập"
    }
    
    analysis_text = f"""
Phân tích kỹ thuật {symbol}: Xu hướng {sentiment_text.get(sentiment, 'trung lập')} với điểm số {sentiment_score:.0%}.

"""
    if rsi:
        analysis_text += f"RSI(14) hiện tại: {rsi:.1f} - "
        if rsi > 70:
            analysis_text += "vùng quá mua. "
        elif rsi < 30:
            analysis_text += "vùng quá bán. "
        else:
            analysis_text += "vùng trung lập. "
    
    if sma_20 and sma_50:
        analysis_text += f"\nSMA(20): {sma_20:.2f}{currency_symbol}, SMA(50): {sma_50:.2f}{currency_symbol}. "
        if sma_20 > sma_50:
            analysis_text += "SMA ngắn > SMA dài: xác nhận xu hướng tăng."
        else:
            analysis_text += "SMA ngắn < SMA dài: xác nhận xu hướng giảm."
    
    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "analysis_vi": analysis_text.strip(),
        "why_moving": why_moving,
        "risks": risks,
        "opportunities": opportunities,
        "key_factors": [
            f"RSI: {rsi:.1f}" if rsi else "RSI: N/A",
            f"MACD: {'+' if macd_hist and macd_hist > 0 else ''}{macd_hist:.2f}" if macd_hist else "MACD: N/A",
            "Xu hướng: " + sentiment_text.get(sentiment, "trung lập"),
        ],
        "fear_greed_index": None,
        "fear_greed_value": None,
    }


# ============================================
# LEGACY ENDPOINTS (KEEP FOR COMPATIBILITY)
# ============================================

@router.get("/{symbol}/history")
async def get_symbol_history(
    symbol: str,
    days: int = Query(default=90, ge=1, le=730),
    db: AsyncSession = Depends(get_db),
):
    """Get historical price data for a symbol."""
    history = await get_price_history(db, symbol, days)
    return {"symbol": symbol, "history": history, "count": len(history)}


@router.get("/{symbol}/indicators")
async def get_technical_indicators(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get latest technical indicators for a symbol."""
    result = await db.execute(
        select(TechnicalIndicator)
        .where(TechnicalIndicator.symbol == symbol)
        .order_by(desc(TechnicalIndicator.date))
        .limit(1)
    )
    indicators = result.scalar_one_or_none()

    if not indicators:
        return {"symbol": symbol, "indicators": None, "error": "No indicators found"}

    return {
        "symbol": symbol,
        "date": indicators.date.isoformat(),
        "indicators": indicators.to_dict(),
    }


@router.get("/{symbol}/analysis")
async def get_market_analysis(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get latest AI market analysis for a symbol."""
    result = await db.execute(
        select(MarketResearch)
        .where(MarketResearch.symbol == symbol)
        .order_by(desc(MarketResearch.analysis_date))
        .limit(1)
    )
    research = result.scalar_one_or_none()

    if not research:
        return {"symbol": symbol, "analysis": None, "error": "No analysis found"}

    return {
        "symbol": symbol,
        "analysis": {
            "sentiment": research.sentiment,
            "sentiment_score": float(research.sentiment_score) if research.sentiment_score else None,
            "analysis_vi": research.analysis_vi,
            "why_moving": research.why_moving or [],
            "risks": research.risks or [],
            "opportunities": research.opportunities or [],
            "fear_greed_index": research.fear_greed_index,
            "confidence_score": float(research.confidence_score) if research.confidence_score else None,
        },
    }


@router.get("/{symbol}/accuracy", response_model=dict)
async def get_symbol_accuracy(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365),
    horizon: Optional[int] = Query(default=None, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get accuracy statistics for a symbol."""
    return await get_accuracy_stats(symbol, days=days, horizon=horizon)


@router.get("/{symbol}/predictions/recent")
async def get_symbol_recent_predictions(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get recent predictions for a symbol."""
    predictions = await get_recent_predictions(symbol, limit=limit)
    return {"symbol": symbol, "predictions": predictions, "count": len(predictions)}


@router.get("/fear-greed")
async def get_fear_greed_index():
    """Get current Fear & Greed index."""
    fg = await fetch_fear_greed()
    if not fg:
        raise HTTPException(status_code=404, detail="Failed to fetch Fear & Greed index")
    return {"value": fg["value"], "value_classification": fg["value_classification"]}


@router.get("/fear-greed/history")
async def get_fear_greed_history(
    days: int = Query(default=30, ge=1, le=365),
):
    """Get Fear & Greed index history."""
    history = await get_fear_greed_data(days=days)
    return {"history": history, "count": len(history)}


@router.get("/alerts/active")
async def get_alerts():
    """Get currently active price alerts."""
    alerts = await get_active_alerts()
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/alerts")
async def create_price_alert(
    symbol: str,
    alert_type: str = Query(default="deviation"),
    threshold_pct: float = Query(default=5.0, ge=0.1, le=50.0),
):
    """Create a new price alert."""
    success = await create_alert(symbol, alert_type, threshold_pct)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create alert")
    return {"message": "Alert created", "symbol": symbol, "type": alert_type, "threshold": threshold_pct}


@router.post("/trigger")
async def trigger_prediction(
    symbol: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger prediction for a symbol or all symbols."""
    from app.prediction.tasks import task_run_full_prediction

    try:
        result = await task_run_full_prediction(symbol=symbol)
        return {
            "message": f"Prediction triggered for {'all symbols' if symbol is None else symbol}",
            **result,
        }
    except Exception as e:
        logger.error(f"Prediction trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HELPER FUNCTIONS
# ============================================

async def _generate_mock_predictions(
    db: AsyncSession,
    symbol: str,
    market: str,
    current_price: float
) -> None:
    """
    Generate mock predictions for VN stocks when no AI predictions exist.
    Uses simple trend analysis based on recent price data.
    """
    try:
        from sqlalchemy.dialects.postgresql import insert
        
        # Get recent history for trend analysis
        result = await db.execute(
            select(PriceHistory)
            .where(func.lower(PriceHistory.symbol) == symbol.lower())
            .order_by(desc(PriceHistory.date))
            .limit(30)
        )
        history = result.scalars().all()
        
        # Calculate trend
        trend = 0.0
        if len(history) >= 7:
            recent_prices = [float(h.close) for h in history[:7] if h.close]
            if len(recent_prices) >= 2:
                # Simple linear trend
                trend = (recent_prices[0] - recent_prices[-1]) / recent_prices[-1] * 100
        
        # Generate predictions for each horizon
        horizons = [
            {'days': 1, 'factor': 1.0 + (trend / 100) * 0.3 + random.uniform(-0.02, 0.02)},
            {'days': 7, 'factor': 1.0 + (trend / 100) * 0.5 + random.uniform(-0.03, 0.03)},
            {'days': 30, 'factor': 1.0 + (trend / 100) * 0.8 + random.uniform(-0.05, 0.05)},
        ]
        
        currency = "VND" if market == "vn" else "USD"
        
        for h in horizons:
            predicted = current_price * h['factor']
            variance = predicted * 0.02  # 2% variance for range
            
            stmt = insert(PredictionFinal).values(
                symbol=symbol,
                market=market,
                currency=currency,
                prediction_date=date.today(),
                horizon_days=h['days'],
                current_price=Decimal(str(current_price)),
                predicted_price=Decimal(str(round(predicted, 2))),
                predicted_low=Decimal(str(round(predicted - variance, 2))),
                predicted_high=Decimal(str(round(predicted + variance, 2))),
                change_pct=Decimal(str(round((predicted - current_price) / current_price * 100, 4))),
                confidence_score=Decimal(str(round(random.uniform(0.85, 0.98), 4))),
                model_used='trend_analysis_mock',
                generated_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'prediction_date', 'horizon_days'],
                set_={
                    'predicted_price': stmt.excluded.predicted_price,
                    'predicted_low': stmt.excluded.predicted_low,
                    'predicted_high': stmt.excluded.predicted_high,
                    'change_pct': stmt.excluded.change_pct,
                    'confidence_score': stmt.excluded.confidence_score,
                    'generated_at': stmt.excluded.generated_at,
                }
            )
            await db.execute(stmt)
        
        await db.commit()
        logger.info(f"Generated mock predictions for {symbol}")
        
    except Exception as e:
        logger.error(f"Failed to generate mock predictions for {symbol}: {e}")
        raise


@router.get("/")
async def get_prediction_status():
    """Get overall prediction system status."""
    return {
        "status": "operational",
        "tracked_symbols": len(DEFAULT_SYMBOLS),
        "prediction_horizons": PREDICTION_HORIZONS,
        "markets": ["crypto", "vn", "us"],
        "models": ["timesfm-2.5", "chronos-2", "ensemble"],
        "last_updated": datetime.utcnow().isoformat(),
    }
