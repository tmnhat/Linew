"""
AI Analyst using MiniMax M2.5 for market research and analysis.
Enhanced with detailed why_moving and risks analysis.

Prediction V3 Upgrade:
- Adaptive weights based on agent performance
- Market regime detection (TRENDING/SIDEWAYS/VOLATILE)
- Multi-timeframe analysis (4h, 1h)
- Options & derivatives signals
- Social sentiment (Lunarcrush, CryptoPanic)
- Cross-asset correlation
"""
import json
import logging
import asyncio
from datetime import date
from decimal import Decimal
from typing import Optional

from app.core.ai_gateway import ai_gateway
from app.prediction.config import AI_ANALYST_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS

logger = logging.getLogger(__name__)


async def analyze_symbol(
    symbol: str,
    symbol_name: str,
    market: str,
    current_price: float,
    price_change_pct: float,
    indicators: dict,
    fear_greed: Optional[dict] = None,
    recent_news: Optional[list[str]] = None,
    currency: str = "USD",
) -> Optional[dict]:
    """
    Analyze a symbol using AI and generate detailed market research.

    Args:
        symbol: Trading symbol (e.g., BTC-USD, AAPL)
        symbol_name: Full name of the asset
        market: Market type (crypto, us)
        current_price: Current price
        price_change_pct: Daily price change percentage
        indicators: Technical indicators dictionary
        fear_greed: Fear & Greed index data
        recent_news: Optional list of recent news headlines
        currency: Currency code (USD)

    Returns:
        Market research data with why_moving, risks, opportunities
    """
    try:
        context = _build_analysis_context(
            symbol, symbol_name, market, current_price, price_change_pct,
            indicators, fear_greed, recent_news, currency
        )

        prompt = _build_analysis_prompt(context)

        response = await ai_gateway.call_ai(
            prompt=prompt,
            model=AI_ANALYST_MODEL,
            task_type="research",
            response_format={"type": "json_object"},
            max_tokens=AI_MAX_TOKENS,
            temperature=AI_TEMPERATURE,
        )

        analysis = _parse_analysis_response(response, symbol, market)

        if analysis:
            await _save_market_research(symbol, market, analysis, fear_greed)

        return analysis

    except Exception as e:
        logger.error(f"AI analysis failed for {symbol}: {e}")
        return None


def _build_analysis_context(
    symbol: str,
    symbol_name: str,
    market: str,
    current_price: float,
    price_change_pct: float,
    indicators: dict,
    fear_greed: Optional[dict],
    recent_news: Optional[list],
    currency: str,
) -> dict:
    """Build analysis context from available data."""

    rsi = indicators.get("rsi_14")
    macd_line = indicators.get("macd_line")
    macd_signal = indicators.get("macd_signal")
    macd_hist = indicators.get("macd_histogram")
    sma_20 = indicators.get("sma_20")
    sma_50 = indicators.get("sma_50")
    sma_200 = indicators.get("sma_200")
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    bb_middle = indicators.get("bb_middle")
    atr = indicators.get("atr_14")
    volume = indicators.get("volume")
    volume_sma_20 = indicators.get("volume_sma_20")

    volume_ratio = None
    if volume and volume_sma_20 and volume_sma_20 > 0:
        volume_ratio = round(volume / volume_sma_20, 2)

    sma_50_vs_200 = None
    if sma_50 and sma_200:
        if sma_50 > sma_200 * 1.02:
            sma_50_vs_200 = "Golden Cross (50 > 200)"
        elif sma_50 < sma_200 * 0.98:
            sma_50_vs_200 = "Death Cross (50 < 200)"
        else:
            sma_50_vs_200 = "Neutral"

    currency_symbol = "$"

    return {
        "symbol": symbol,
        "symbol_name": symbol_name,
        "market": market,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "current_price": current_price,
        "price_change_pct": price_change_pct,
        "technical_indicators": {
            "rsi": rsi,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_hist,
            "bb_upper": bb_upper,
            "bb_middle": bb_middle,
            "bb_lower": bb_lower,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "atr": atr,
            "volume": volume,
            "volume_ratio": volume_ratio,
            "sma_50_vs_200": sma_50_vs_200,
        },
        "fear_greed": fear_greed,
        "recent_news": recent_news or [],
    }


def _build_analysis_prompt(context: dict) -> str:
    """Build detailed analysis prompt for AI with market-specific context."""

    sym = context["symbol"]
    sym_name = context["symbol_name"]
    market = context["market"]
    price = context["current_price"]
    change = context["price_change_pct"]
    currency_sym = context["currency_symbol"]
    ind = context["technical_indicators"]
    fg = context.get("fear_greed")

    def fmt(v):
        if v is None:
            return "N/A"
        if isinstance(v, (int, float)):
            return f"{currency_sym}{v:,.2f}"
        return str(v)

    def fmt_num(v):
        if v is None:
            return "N/A"
        return f"{v:,.2f}"

    rsi = fmt_num(ind.get("rsi"))
    macd = fmt_num(ind.get("macd_line"))
    macd_sig = fmt_num(ind.get("macd_signal"))
    macd_hist = fmt_num(ind.get("macd_histogram"))
    bb_up = fmt(ind.get("bb_upper"))
    bb_mid = fmt(ind.get("bb_middle"))
    bb_low = fmt(ind.get("bb_lower"))
    sma20 = fmt(ind.get("sma_20"))
    sma50 = fmt(ind.get("sma_50"))
    sma200 = fmt(ind.get("sma_200"))
    atr = fmt_num(ind.get("atr"))
    vol_ratio = f"{ind.get('volume_ratio', 'N/A')}x"
    sma_cross = ind.get("sma_50_vs_200", "N/A")

    fg_val = fg.get("value", "N/A") if fg else "N/A"
    fg_class = fg.get("value_classification", "N/A") if fg else "N/A"

    news = context.get("recent_news", []) or []
    news_section = ""
    if news and len(news) > 0:
        news_items = "\n".join([f"- {n}" for n in news[:5]])
        news_section = f"""

TIN TUC GAN DAY:
{news_items}
"""

    prompt = f"""Ban la "Linews Analysis" — he thong phan tich tai chinh chuyen nghiep.

Phan tich CHI TIET cho {sym_name} ({sym}):

DU LIEU HIEN TAI:
- Gia hien tai: {currency_sym}{price:,.2f}
- Bien dong 24h: {change:+.2f}%

CHI SO KY THUAT:
- RSI (14): {rsi}
- MACD: {macd} (Signal: {macd_sig}, Histogram: {macd_hist})
- Bollinger Bands: Upper {bb_up}, Middle {bb_mid}, Lower {bb_low}
- SMA(20): {sma20}
- SMA(50): {sma50}
- SMA(200): {sma200}
- SMA 50 vs 200: {sma_cross}
- ATR(14): {atr}
- Volume so voi TB 20 ngay: {vol_ratio}
{news_section}"""

    if market == "crypto":
        prompt += f"""
Fear & Greed Index: {fg_val}/100 ({fg_class})

YEU CAU PHAN TICH CRYPTO:
1. Tim 3-5 tin tuc QUAN TRONG NHAT anh huong {sym_name} trong 7 ngay qua
2. Phan tich dong tien ETF, on-chain data, whale movement (neu relevant)
3. Su kien macro: Fed, CPI, quy dinh crypto tai cac quoc gia lon
4. Sentiment thi truong crypto tong the
"""
    elif market == "us":
        prompt += f"""
San: {context.get('exchange', 'NASDAQ')}

YEU CAU PHAN TICH CHUNG KHOAN MY:
1. Tim tin tuc MOI NHAT ve {sym_name} — earnings, product launch, CEO statements
2. Phan tich so voi competitors trong nganh
3. Institutional ownership changes gan day
4. Tac dong tu Fed policy, US economic data
5. Analyst ratings va price targets gan nhat
"""

    prompt += f"""

QUAN TRONG — Tra loi CHINH XAC JSON format sau:
{{
    "sentiment": "positive" | "neutral" | "negative",
    "sentiment_score": 0.0-1.0,

    "why_moving": [
        "Ly do cu the 1 giai thich tai sao gia dang tang/giam (tieng Viet, 1-2 cau)",
        "Ly do cu the 2 (tieng Viet, 1-2 cau)",
        "Ly do cu the 3 (tieng Viet, 1-2 cau)"
    ],

    "risks": [
        "Rui ro cu the 1 co the anh huong tieu cu nhu (tieng Viet, 1-2 cau)",
        "Rui ro cu the 2 (tieng Viet, 1-2 cau)"
    ],

    "opportunities": [
        "Co hoi cu the 1 (tieng Viet, 1-2 cau)",
        "Co hoi cu the 2 (tieng Viet, 1-2 cau)"
    ],

    "key_factors": ["yeu to 1", "yeu to 2", "yeu to 3"],

    "news_summary_vi": "Tom tat 3-5 tin quan trong nhat bang tieng Viet",

    "analysis_vi": "Phan tich tong hop 4-6 cau bang tieng Viet. Viet nhu chuyen gia tai chinh. KHONG nhac ten model hay AI. Viet nhu day la phan tich cua Linews.",

    "confidence_score": 0.0-1.0
}}

LUU Y:
- why_moving phai giai thich CUNG THE voi so lieu neu co
- risks phai la rui ro THUC TE, khong chung chung
- opportunities la cac yeu to ho tro gia tang
- Tat ca text bang TIENG VIET
- KHONG nhac ten TimesFM, Chronos-2, MiniMax, hay bat ky AI model nao
"""

    return prompt


def _parse_analysis_response(response: dict, symbol: str, market: str) -> Optional[dict]:
    """Parse AI response into market research format."""
    try:
        text = response.get("text", "")

        if isinstance(response, dict) and "sentiment" in response:
            return _normalize_response(response)

        if text:
            try:
                analysis = json.loads(text)
                if "sentiment" in analysis:
                    return _normalize_response(analysis)
            except json.JSONDecodeError:
                pass

        logger.warning(f"Invalid AI response format for {symbol}")
        return None

    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}")
        return None


def _normalize_response(analysis: dict) -> dict:
    """Normalize AI response to consistent format."""
    sentiment = analysis.get("sentiment", "neutral")

    sentiment_map = {
        "bullish": "positive",
        "bearish": "negative",
        "positive": "positive",
        "negative": "negative",
    }
    sentiment = sentiment_map.get(sentiment.lower(), sentiment)

    return {
        "sentiment": sentiment,
        "sentiment_score": float(analysis.get("sentiment_score", 0.5)),
        "why_moving": analysis.get("why_moving", []),
        "risks": analysis.get("risks", []),
        "opportunities": analysis.get("opportunities", []),
        "key_factors": analysis.get("key_factors", []),
        "news_summary_vi": analysis.get("news_summary_vi", ""),
        "analysis_vi": analysis.get("analysis_vi", ""),
        "confidence_score": float(analysis.get("confidence_score", 0.5)),
    }


async def _save_market_research(
    symbol: str,
    market: str,
    analysis: dict,
    fear_greed: Optional[dict]
) -> bool:
    """Save market research to database."""
    from app.core.database import get_db_context
    from app.models.prediction_models import MarketResearch
    from sqlalchemy.dialects.postgresql import insert

    try:
        async with get_db_context() as session:
            today = date.today()

            sentiment_score = Decimal(str(analysis.get("sentiment_score", 0.5)))
            confidence = Decimal(str(analysis.get("confidence_score", 0.5)))

            why_moving = analysis.get("why_moving", [])
            risks = analysis.get("risks", [])
            opportunities = analysis.get("opportunities", [])
            key_factors = analysis.get("key_factors", [])

            stmt = insert(MarketResearch).values(
                symbol=symbol,
                analysis_date=today,
                sentiment=analysis.get("sentiment"),
                sentiment_score=sentiment_score,
                analysis_text=analysis.get("analysis_text"),
                analysis_vi=analysis.get("analysis_vi"),
                key_factors=key_factors,
                risk_factors=risks,
                why_moving=why_moving,
                risks=risks,
                opportunities=opportunities,
                support_levels=analysis.get("support_levels", []),
                resistance_levels=analysis.get("resistance_levels", []),
                fear_greed_index=fear_greed.get("value") if fear_greed else None,
                fear_greed_value=fear_greed.get("value_classification") if fear_greed else None,
                model_used=AI_ANALYST_MODEL,
                confidence_score=confidence,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "analysis_date"],
                set_={
                    "sentiment": stmt.excluded.sentiment,
                    "sentiment_score": stmt.excluded.sentiment_score,
                    "analysis_text": stmt.excluded.analysis_text,
                    "analysis_vi": stmt.excluded.analysis_vi,
                    "key_factors": stmt.excluded.key_factors,
                    "risk_factors": stmt.excluded.risk_factors,
                    "why_moving": stmt.excluded.why_moving,
                    "risks": stmt.excluded.risks,
                    "opportunities": stmt.excluded.opportunities,
                    "support_levels": stmt.excluded.support_levels,
                    "resistance_levels": stmt.excluded.resistance_levels,
                    "fear_greed_index": stmt.excluded.fear_greed_index,
                    "fear_greed_value": stmt.excluded.fear_greed_value,
                    "confidence_score": stmt.excluded.confidence_score,
                }
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Saved market research for {symbol}")
            return True

    except Exception as e:
        logger.error(f"Failed to save market research for {symbol}: {e}")
        return False


async def get_latest_analysis(symbol: str) -> Optional[dict]:
    """Get the latest market research for a symbol."""
    from sqlalchemy import select, desc
    from app.core.database import get_db_context
    from app.models.prediction_models import MarketResearch

    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(MarketResearch)
                .where(MarketResearch.symbol == symbol)
                .order_by(desc(MarketResearch.analysis_date))
                .limit(1)
            )
            research = result.scalar_one_or_none()

            if research:
                return {
                    "sentiment": research.sentiment,
                    "sentiment_score": float(research.sentiment_score) if research.sentiment_score else None,
                    "analysis_vi": research.analysis_vi,
                    "why_moving": research.why_moving or [],
                    "risks": research.risks or [],
                    "opportunities": research.opportunities or [],
                    "key_factors": research.key_factors or [],
                    "fear_greed_index": research.fear_greed_index,
                    "confidence_score": float(research.confidence_score) if research.confidence_score else None,
                }
            return None
    except Exception as e:
        logger.error(f"Failed to get latest analysis for {symbol}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-AGENT AI ANALYSIS (Prediction V3)
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_STYLES = {
    "trend": {
        "name": "Trend Agent",
        "description": "Phan tich xu huong ky thuat va dong luong",
        "instructions": "Ban la chuyen gia phan tich ky thuat. Phan tich cac chi bao ky thuat (RSI, MACD, Bollinger Bands, SMA), xu huong gia, va dong luong. Dua ra du bao ngan han dua tren price action.",
        "weight": 0.25,
    },
    "value": {
        "name": "Value Agent",
        "description": "Phan tich gia tri co ban va dinh gia",
        "instructions": "Ban la chuyen gia dinh gia. Phan tich P/E, P/B, EPS, doanh thu, loi nhuan, dong tien, va so sanh voi doi thu. Danh gia co phieu/crypto co dang bi dinh gia thap hay cao.",
        "weight": 0.25,
    },
    "macro": {
        "name": "Macro Agent",
        "description": "Phan tich vi mo va dieu kien thi truong",
        "instructions": "Ban la chuyen gia kinh te vi mo. Phan tich tac dong cua Fed, lai suat, CPI, GDP, VIX, DXY, va dieu kien thanh khoan. Danh gia rui ro va co hoi tu moi truong vi mo.",
        "weight": 0.20,
    },
    "sentiment": {
        "name": "Sentiment Agent",
        "description": "Phan tich tam ly thi truong",
        "instructions": "Ban la chuyen gia phan tich tam ly. Phan tich tin tuc, Fear & Greed Index, khoi luong giao dich, va dinh huong dong tien. Danh gia tam ly dam dong va kha nang dao chieu.",
        "weight": 0.15,
    },
    "onchain": {
        "name": "OnChain Agent",
        "description": "Phan tich du lieu on-chain (crypto)",
        "instructions": "Ban la chuyen gia phan tich on-chain. Phan tich TVL, whale activity, exchange flows, staking yields, va DeFi metrics. Danh gia suc manh network va xu huong dong tien.",
        "weight": 0.15,
    },
}


async def analyze_symbol_enhanced(
    symbol: str,
    symbol_name: str,
    market: str,
    current_price: float,
    price_change_pct: float,
    indicators: dict,
    fundamentals: Optional[dict] = None,
    macro_data: Optional[dict] = None,
    onchain_data: Optional[dict] = None,
    events: Optional[dict] = None,
    fear_greed: Optional[dict] = None,
    recent_news: Optional[list[str]] = None,
    currency: str = "USD",
    price_history: Optional[list[dict]] = None,
) -> Optional[dict]:
    """
    Enhanced multi-agent analysis V3 voi day du L1-L5 + MTF + Options + Social + Correlation.

    Thu tu uu tien data: cache -> fresh fetch -> graceful fallback (khong bao gio crash).

    Phase A: Adaptive weights + Regime detection + MTF
    Phase B: Options signals + Social sentiment + Correlation
    """
    try:
        from app.prediction.config import AGENT_STYLES_ENABLED
        from app.config import get_settings
        settings = get_settings()

        # =========================================================================
        # BUOC 1: Gather all data layers song song
        # =========================================================================
        tasks = {}
        mtf_data = options_data = social_data = correlation_data = None

        # Phase A3: Multi-timeframe (crypto + US only)
        if market in ("crypto", "us") and settings.prediction_enable_mtf:
            from app.prediction.multi_timeframe import get_mtf_indicators
            tasks["mtf"] = get_mtf_indicators(symbol, market)

        # Phase B1: Options signals (US + BTC/ETH)
        if market in ("us", "crypto") and settings.prediction_enable_options:
            from app.prediction.options_signals import get_options_signals
            tasks["options"] = get_options_signals(symbol, market)

        # Phase B2: Social sentiment (all markets)
        if settings.prediction_enable_social:
            from app.prediction.social_sentiment import get_social_sentiment
            tasks["social"] = get_social_sentiment(symbol, market)

        # Phase B3: Correlation (crypto + US)
        if market in ("crypto", "us") and settings.prediction_enable_correlation:
            from app.prediction.correlation_engine import get_correlation_context
            tasks["correlation"] = get_correlation_context(symbol, market)

        # Execute all tasks in parallel
        if tasks:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.debug(f"Task {key} failed: {result}")
                    continue
                if key == "mtf":
                    mtf_data = result
                elif key == "options":
                    options_data = result
                elif key == "social":
                    social_data = result
                elif key == "correlation":
                    correlation_data = result

        # =========================================================================
        # BUOC 2: Detect market regime
        # =========================================================================
        regime_info = {
            "regime": "SIDEWAYS",
            "signal_threshold": 0.35,
            "weight_adjustments": {},
            "description": "Thi truong di ngang, cho tin hieu ro hon"
        }

        if settings.prediction_enable_regime_detection:
            from app.prediction.regime_detector import detect_regime, apply_regime_to_weights

            # Extract highs, lows, closes from price_history if available
            highs = lows = closes = None
            if price_history:
                highs  = [float(h["high"]) for h in price_history if h.get("high")]
                lows   = [float(h["low"])  for h in price_history if h.get("low")]
                closes = [float(h["close"]) for h in price_history if h.get("close")]

            regime_info = detect_regime(indicators, highs, lows, closes)
            logger.info(f"Regime [{symbol}]: {regime_info['regime']} | Threshold={regime_info.get('signal_threshold')}")

        # =========================================================================
        # BUOC 3: Lay adaptive weights + apply regime adjustments
        # =========================================================================
        current_weights = {k: dict(v) for k, v in AGENT_STYLES.items()}

        if settings.prediction_enable_adaptive_weights:
            from app.prediction.adaptive_weights import get_agent_weights
            try:
                cached_weights = await get_agent_weights(market if market in ("crypto", "us") else "all")
                for key in current_weights:
                    if key in cached_weights:
                        current_weights[key]["weight"] = cached_weights[key]
            except Exception as e:
                logger.debug(f"Failed to get adaptive weights: {e}")

        # Apply regime adjustments
        if regime_info.get("weight_adjustments"):
            from app.prediction.regime_detector import apply_regime_to_weights
            base = {k: v["weight"] for k, v in current_weights.items()}
            adjusted = apply_regime_to_weights(base, regime_info)
            for key in current_weights:
                if key in adjusted:
                    current_weights[key]["weight"] = adjusted[key]

        # =========================================================================
        # BUOC 4: Format context strings
        # =========================================================================
        mtf_str  = mtf_data.get("mtf_context_str", "") if mtf_data else ""
        opts_str = options_data.get("interpretation", "") if options_data else ""
        soc_str  = social_data.get("social_context_str", "") if social_data else ""
        corr_str = correlation_data.get("context_str", "") if correlation_data else ""

        regime_str = (
            f"REGIME: {regime_info['regime']} - {regime_info.get('description', '')}\n"
            f"Signal threshold: {regime_info.get('signal_threshold', 0.35):.0%} conviction required"
        )

        # =========================================================================
        # BUOC 5: Chay multi-agent
        # =========================================================================
        if settings.prediction_enable_multi_agent:
            # Determine which agents to run
            agents_to_run = [
                style for style in AGENT_STYLES
                if AGENT_STYLES_ENABLED.get(style, True)
                and (style != "onchain" or market == "crypto")  # onchain chi cho crypto
            ]

            # Run all agents in parallel
            agent_tasks = [
                _run_single_agent_v3(
                    agent_type=agent_type,
                    symbol=symbol,
                    symbol_name=symbol_name,
                    market=market,
                    current_price=current_price,
                    price_change_pct=price_change_pct,
                    indicators=indicators,
                    fundamentals=fundamentals,
                    macro_data=macro_data,
                    onchain_data=onchain_data,
                    events=events,
                    fear_greed=fear_greed,
                    recent_news=recent_news,
                    currency=currency,
                    mtf_str=mtf_str,
                    options_str=opts_str,
                    social_str=soc_str,
                    corr_str=corr_str,
                    regime_str=regime_str,
                )
                for agent_type in agents_to_run
            ]

            results = await asyncio.gather(*agent_tasks, return_exceptions=True)

            # Collect valid agent results
            agent_signals = []
            for agent_type, result in zip(agents_to_run, results):
                if isinstance(result, dict) and "error" not in result:
                    result["agent_type"] = agent_type
                    result["weight"] = current_weights[agent_type]["weight"]
                    agent_signals.append(result)

            if not agent_signals:
                logger.warning(f"No valid agent results for {symbol}")
                return None

            # Compute weighted consensus with regime threshold
            threshold = regime_info.get("signal_threshold", 0.35)
            consensus = _compute_weighted_consensus_v2(
                agent_signals, symbol, symbol_name, market, current_price, threshold=threshold
            )

            # Add regime info to consensus
            if consensus:
                consensus["regime"] = regime_info.get("regime")
                consensus["regime_threshold"] = threshold

                # Add MTF signal if available
                if mtf_data:
                    consensus["mtf_signal"] = mtf_data.get("mtf_signal", "NEUTRAL")

                # Add options signal if available
                if options_data:
                    consensus["options_signal"] = options_data.get("options_signal", "NEUTRAL")

                # Calibrate confidence if enabled
                if settings.prediction_calibration_enabled:
                    try:
                        from app.prediction.accuracy_tracker import get_calibrated_confidence
                        consensus["confidence_score"] = await get_calibrated_confidence(
                            consensus.get("confidence_score", 0.5)
                        )
                    except Exception:
                        pass

            await _save_market_research(symbol, market, consensus, fear_greed)
            return consensus

        # Fallback: single agent analysis
        return await analyze_symbol(
            symbol=symbol,
            symbol_name=symbol_name,
            market=market,
            current_price=current_price,
            price_change_pct=price_change_pct,
            indicators=indicators,
            fear_greed=fear_greed,
            recent_news=recent_news,
            currency=currency,
        )

    except Exception as e:
        logger.error(f"Enhanced analysis failed for {symbol}: {e}")
        return None


async def _run_single_agent_v3(
    agent_type: str,
    symbol: str,
    symbol_name: str,
    market: str,
    current_price: float,
    price_change_pct: float,
    indicators: dict,
    fundamentals: Optional[dict],
    macro_data: Optional[dict],
    onchain_data: Optional[dict],
    events: Optional[dict],
    fear_greed: Optional[dict],
    recent_news: Optional[list[str]],
    currency: str,
    mtf_str: str = "",
    options_str: str = "",
    social_str: str = "",
    corr_str: str = "",
    regime_str: str = "",
) -> dict:
    """Run a single specialized agent V3 with additional context."""
    style = AGENT_STYLES.get(agent_type, {})
    agent_name = style.get("name", agent_type.capitalize())

    # Build context for this agent
    context = _build_agent_context_v3(
        agent_type, symbol, symbol_name, market, current_price, price_change_pct,
        indicators, fundamentals, macro_data, onchain_data, events, fear_greed,
        recent_news, currency, mtf_str, options_str, social_str, corr_str, regime_str
    )

    prompt = _build_agent_prompt_v3(agent_type, context)

    try:
        response = await ai_gateway.call_ai(
            prompt=prompt,
            model=AI_ANALYST_MODEL,
            task_type="research",
            response_format={"type": "json_object"},
            max_tokens=AI_MAX_TOKENS // 2,
            temperature=AI_TEMPERATURE,
        )

        if isinstance(response, dict) and "sentiment" in response:
            return response
        elif isinstance(response, dict) and "text" in response:
            try:
                return json.loads(response["text"])
            except json.JSONDecodeError:
                return {"error": "Invalid response format"}

        return {"error": "No valid response"}

    except Exception as e:
        logger.error(f"Agent {agent_type} failed for {symbol}: {e}")
        return {"error": str(e)}


def _build_agent_context_v3(
    agent_type, symbol, symbol_name, market, current_price, price_change_pct,
    indicators, fundamentals, macro_data, onchain_data, events, fear_greed,
    recent_news, currency, mtf_str, options_str, social_str, corr_str, regime_str
) -> dict:
    """Build context data for a specific agent type V3."""
    currency_sym = "$"

    base = {
        "symbol": symbol,
        "symbol_name": symbol_name,
        "market": market,
        "currency_sym": currency_sym,
        "current_price": current_price,
        "price_change_pct": price_change_pct,
        "indicators": indicators,
        "fear_greed": fear_greed,
        "recent_news": recent_news or [],
        "mtf_str": mtf_str,
        "options_str": options_str,
        "social_str": social_str,
        "corr_str": corr_str,
        "regime_str": regime_str,
    }

    if agent_type in ("value", "macro") and fundamentals:
        base["fundamentals"] = fundamentals

    if agent_type in ("macro", "onchain") and macro_data:
        base["macro_data"] = macro_data

    if agent_type == "onchain" and onchain_data:
        base["onchain_data"] = onchain_data

    if agent_type in ("macro", "sentiment") and events:
        base["events"] = events

    return base


def _build_agent_prompt_v3(agent_type: str, context: dict) -> str:
    """Build prompt for a specific agent type V3 with regime and MTF context."""
    style = AGENT_STYLES.get(agent_type, {})
    instructions = style.get("instructions", "")

    sym = context["symbol"]
    sym_name = context["symbol_name"]
    market = context["market"]
    price = context["current_price"]
    change = context["price_change_pct"]
    currency_sym = context["currency_sym"]
    ind = context.get("indicators", {})

    prompt = f"""Ban la {style.get("name", agent_type)}.

{instructions}

## Symbol: {sym} ({sym_name})
## Thi truong: {market.upper()}
## Gia hien tai: {currency_sym}{price:,.2f}
## Thay doi 24h: {change:+.2f}%

## Chi bao ky thuat:
- RSI(14): {ind.get('rsi_14', 'N/A')}
- MACD: {ind.get('macd_line', 'N/A')} | Signal: {ind.get('macd_signal', 'N/A')} | Hist: {ind.get('macd_histogram', 'N/A')}
- Bollinger Bands: Upper {currency_sym}{ind.get('bb_upper', 0):,.2f} | Mid {currency_sym}{ind.get('bb_middle', 0):,.2f} | Lower {currency_sym}{ind.get('bb_lower', 0):,.2f}
- SMA(20/50/200): {currency_sym}{ind.get('sma_20', 0):,.2f} / {currency_sym}{ind.get('sma_50', 0):,.2f} / {currency_sym}{ind.get('sma_200', 0):,.2f}
- ATR(14): {ind.get('atr_14', 'N/A')}
- ADX(14): {ind.get('adx_14', 'N/A')}
"""

    # Add specialized context based on agent type
    if agent_type == "value" and "fundamentals" in context:
        fund = context["fundamentals"]
        prompt += f"""
## Du lieu co ban:
- P/E: {fund.get('pe_ratio', 'N/A')}
- EPS: {fund.get('eps', 'N/A')}
- Market Cap: {fund.get('market_cap', 'N/A')}
- Revenue Growth: {fund.get('revenue_growth', 'N/A')}%
- ROE: {fund.get('roe', 'N/A')}%
- Profit Margin: {fund.get('profit_margin', 'N/A')}%
- Beta: {fund.get('beta', 'N/A')}
"""

    if agent_type == "macro" and "macro_data" in context:
        macro = context["macro_data"]
        prompt += f"""
## Du lieu vi mo:
- Fed Funds Rate: {macro.get('fed_funds_rate', {}).get('value', 'N/A')}%
- CPI: {macro.get('cpi', {}).get('value', 'N/A')}
- VIX: {macro.get('vix', {}).get('value', 'N/A')}
- DXY: {macro.get('dxy', {}).get('value', 'N/A')}
"""

    if agent_type == "onchain" and "onchain_data" in context:
        onchain = context["onchain_data"]
        prompt += f"""
## Du lieu On-Chain:
- Total DeFi TVL: ${onchain.get('total_defi_tvl', 'N/A')}
- ETH Staking Yield: {onchain.get('eth_staking_yield', 'N/A')}%
"""

    if agent_type in ("macro", "sentiment") and "events" in context:
        events_data = context["events"]
        fomc = events_data.get("fomc", [])
        if fomc:
            prompt += f"""
## Su kien sap toi:
- FOMC: {fomc[0].get('date', 'N/A')} - {fomc[0].get('description', 'N/A')}
"""

    # Add V3 context blocks
    if context.get("regime_str"):
        prompt += f"\n{context['regime_str']}\n"

    if agent_type == "trend" and context.get("mtf_str"):
        prompt += f"\n{context['mtf_str']}\n"

    if agent_type in ("sentiment", "trend") and context.get("options_str"):
        prompt += f"\nOPTIONS: {context['options_str']}\n"

    if agent_type == "sentiment" and context.get("social_str"):
        prompt += f"\n{context['social_str']}\n"

    if agent_type == "macro" and context.get("corr_str"):
        prompt += f"\n{context['corr_str']}\n"

    if context.get("fear_greed"):
        fg = context["fear_greed"]
        prompt += f"""
## Fear & Greed Index: {fg.get('value', 'N/A')} ({fg.get('value_classification', 'N/A')})
"""

    if context.get("recent_news"):
        news = context["recent_news"][:3]
        prompt += f"""
## Tin tuc gan day:
{chr(10).join([f"- {n}" for n in news])}
"""

    prompt += """
Tra loi CHINH XAC JSON format sau:
{
    "sentiment": "positive" | "neutral" | "negative",
    "sentiment_score": 0.0-1.0,
    "confidence_score": 0.0-1.0,
    "key_signal": "Tin hieu chinh tu goc nhin cua ban (1 cau tieng Viet)",
    "reasons": ["Ly do 1", "Ly do 2", "Ly do 3"]
}

KHONG nhac ten model hay AI. Viet nhu chuyen gia phan tich thuc thu.
"""

    return prompt


def _compute_weighted_consensus_v2(
    agent_signals: list,
    symbol: str,
    symbol_name: str,
    market: str,
    current_price: float,
    threshold: float = 0.35,
) -> dict:
    """Combine agent signals into weighted consensus V2 with regime threshold."""
    sentiment_scores = []
    confidence_scores = []

    for agent in agent_signals:
        if "error" in agent:
            continue

        score = agent.get("sentiment_score", 0.5)
        weight = agent.get("weight", 0.0)

        # Convert sentiment to numeric
        sentiment_map = {"negative": -1, "neutral": 0, "positive": 1}
        sent_val = sentiment_map.get(agent.get("sentiment", "neutral"), 0)

        # Weighted score
        sentiment_scores.append((score * sent_val, weight))
        confidence_scores.append((agent.get("confidence_score", 0.5), weight))

    if not sentiment_scores:
        return None

    # Compute weighted average
    total_weight = sum(w for _, w in sentiment_scores)
    if total_weight == 0:
        total_weight = 1

    weighted_sentiment = sum(s * w for s, w in sentiment_scores) / total_weight
    weighted_confidence = sum(c * w for c, w in confidence_scores) / total_weight

    # Map back to sentiment label using regime threshold
    if weighted_sentiment > threshold:
        final_sentiment = "positive"
    elif weighted_sentiment < -threshold:
        final_sentiment = "negative"
    else:
        final_sentiment = "neutral"

    # Collect all reasons from agents
    all_reasons = []
    for agent in agent_signals:
        if "reasons" in agent and "error" not in agent:
            all_reasons.extend(agent["reasons"][:2])

    # Generate consensus analysis
    consensus = {
        "symbol": symbol,
        "symbol_name": symbol_name,
        "market": market,
        "current_price": current_price,
        "sentiment": final_sentiment,
        "sentiment_score": round(abs(weighted_sentiment), 2),
        "confidence_score": round(weighted_confidence, 2),
        "agent_count": len(agent_signals),
        "agent_signals": [
            {
                "agent_type": a.get("agent_type"),
                "agent_name": AGENT_STYLES.get(a.get("agent_type", ""), {}).get("name", a.get("agent_type", "")),
                "sentiment": a.get("sentiment"),
                "sentiment_score": a.get("sentiment_score"),
                "key_signal": a.get("key_signal", ""),
            }
            for a in agent_signals if "error" not in a
        ],
        "why_moving": list(dict.fromkeys(all_reasons[:6])),
        "analysis_vi": _generate_consensus_narrative(final_sentiment, abs(weighted_sentiment), len(agent_signals), symbol),
    }

    return consensus


def _generate_consensus_narrative(sentiment: str, score: float, agent_count: int, symbol: str) -> str:
    """Generate a narrative summary from the consensus."""
    if sentiment == "positive":
        tone = "lac quan"
        outlook = "tang"
    elif sentiment == "negative":
        tone = "than trong"
        outlook = "giam"
    else:
        tone = "trung lap"
        outlook = "sideways"

    return (
        f"Phan tich da tac tu ({agent_count} chuyen gia): "
        f"Tam ly thi truong {tone} voi diem so {score:.0%}. "
        f"Khuyen nghi theo doi sat dien bien {symbol} trong ngan han."
    )


# Backward compatibility
async def _run_single_agent(
    agent_type: str,
    symbol: str,
    symbol_name: str,
    market: str,
    current_price: float,
    price_change_pct: float,
    indicators: dict,
    fundamentals: Optional[dict],
    macro_data: Optional[dict],
    onchain_data: Optional[dict],
    events: Optional[dict],
    fear_greed: Optional[dict],
    recent_news: Optional[list[str]],
    currency: str,
) -> dict:
    """Backward compatible wrapper for _run_single_agent_v3."""
    return await _run_single_agent_v3(
        agent_type=agent_type,
        symbol=symbol,
        symbol_name=symbol_name,
        market=market,
        current_price=current_price,
        price_change_pct=price_change_pct,
        indicators=indicators,
        fundamentals=fundamentals,
        macro_data=macro_data,
        onchain_data=onchain_data,
        events=events,
        fear_greed=fear_greed,
        recent_news=recent_news,
        currency=currency,
        mtf_str="",
        options_str="",
        social_str="",
        corr_str="",
        regime_str="",
    )
