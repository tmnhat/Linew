"""
SQLite Archive Writer - writes PostgreSQL data to monthly SQLite archive files.
Each data type gets its own directory, each month gets its own .db file.
"""
import glob
import json
import logging
import os
import sqlite3
import threading
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


class SQLiteArchiveWriter:
    """Write data from PostgreSQL to monthly SQLite archive files."""

    # Class-level lock registry for per-file locking
    _file_locks: dict = {}
    _file_locks_mutex = threading.Lock()

    def __init__(self, base_dir: str = "/data/archive"):
        self.base_dir = base_dir

    def _get_file_lock(self, db_path: str) -> threading.Lock:
        """Get or create a per-file threading lock."""
        with self._file_locks_mutex:
            if db_path not in self._file_locks:
                self._file_locks[db_path] = threading.Lock()
            return self._file_locks[db_path]

    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """Get SQLite connection with WAL mode and timeout for safe concurrent access."""
        conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")    # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety & performance
        conn.execute("PRAGMA busy_timeout=30000")  # 30s busy wait
        return conn

    def get_db_path(self, data_type: str, year: int, month: int) -> str:
        """
        Get path for SQLite archive file.
        data_type: 'signals', 'articles', 'predictions', 'market_research'
        Returns: /data/archive/signals/2026-04.db
        """
        dir_path = os.path.join(self.base_dir, data_type)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{year}-{month:02d}.db")

    def _ensure_table_exists(self, conn: sqlite3.Connection, data_type: str) -> None:
        """Create table schema based on data type."""
        if data_type == "signals":
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_signals (
                    id TEXT PRIMARY KEY,
                    source_id TEXT,
                    source_name TEXT NOT NULL,
                    feed_url TEXT,
                    feed_title TEXT,
                    original_url TEXT NOT NULL,
                    original_title TEXT NOT NULL,
                    original_summary TEXT,
                    original_content TEXT,
                    original_html TEXT,
                    original_image_url TEXT,
                    original_author TEXT,
                    original_language TEXT,
                    original_tags TEXT,
                    published_at TEXT,
                    url_hash TEXT,
                    title_hash TEXT,
                    content_hash TEXT,
                    word_count INTEGER,
                    has_image INTEGER,
                    was_processed INTEGER,
                    article_id TEXT,
                    processing_result TEXT,
                    processing_note TEXT,
                    processed_at TEXT,
                    is_archived INTEGER,
                    archived_at TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON raw_signals (created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON raw_signals (url_hash)")

        elif data_type == "articles":
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    source_id TEXT,
                    original_url TEXT NOT NULL,
                    original_title TEXT NOT NULL,
                    title_hash TEXT,
                    original_summary TEXT,
                    original_image_url TEXT,
                    signal_published_at TEXT,
                    category TEXT,
                    category_confidence REAL,
                    trend_score REAL,
                    article_type TEXT,
                    crawled_content TEXT,
                    crawled_images TEXT,
                    body_html TEXT,
                    meta_title TEXT,
                    meta_description TEXT,
                    slug TEXT,
                    tags TEXT,
                    image_keywords TEXT,
                    word_count INTEGER,
                    governance_result TEXT,
                    governance_reason TEXT,
                    copyright_score REAL,
                    wp_post_id INTEGER,
                    wp_url TEXT,
                    featured_image_wp_id INTEGER,
                    image_source_credit TEXT,
                    published_at TEXT,
                    state TEXT,
                    mode TEXT,
                    priority INTEGER,
                    queued_at TEXT,
                    fail_reason TEXT,
                    retry_count INTEGER,
                    last_step_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON articles (created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_state ON articles (state)")

        elif data_type == "predictions":
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_final (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    prediction_date TEXT NOT NULL,
                    horizon_days INTEGER NOT NULL,
                    current_price REAL,
                    predicted_price REAL NOT NULL,
                    predicted_low REAL,
                    predicted_high REAL,
                    change_pct REAL,
                    confidence_score REAL,
                    timesfm_prediction REAL,
                    chronos_prediction REAL,
                    ensemble_weight_timesfm REAL,
                    ensemble_weight_chronos REAL,
                    ai_sentiment TEXT,
                    ai_sentiment_score REAL,
                    ai_adjustment_pct REAL,
                    technical_signals TEXT,
                    model_used TEXT NOT NULL,
                    actual_price REAL,
                    accuracy_error_pct REAL,
                    generated_at TEXT,
                    UNIQUE(symbol, prediction_date, horizon_days)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON prediction_final (symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_generated ON prediction_final (generated_at)")

        elif data_type == "market_research":
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_research (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    analysis_date TEXT NOT NULL,
                    sentiment TEXT,
                    sentiment_score REAL,
                    analysis_text TEXT,
                    analysis_vi TEXT,
                    key_factors TEXT,
                    risk_factors TEXT,
                    support_levels TEXT,
                    resistance_levels TEXT,
                    fear_greed_index INTEGER,
                    fear_greed_value TEXT,
                    model_used TEXT,
                    confidence_score REAL,
                    generated_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON market_research (symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_generated ON market_research (generated_at)")

    def write_signals(self, year: int, month: int, signals: list) -> int:
        """Archive raw_signals for the specified month."""
        if not signals:
            return 0

        db_path = self.get_db_path("signals", year, month)
        file_lock = self._get_file_lock(db_path)

        with file_lock:  # Serialise writes from multiple threads
            conn = self._get_connection(db_path)
            self._ensure_table_exists(conn, "signals")

            for signal in signals:
                try:
                    tags_json = json.dumps(signal.original_tags) if signal.original_tags else "[]"
                    conn.execute("""
                        INSERT OR REPLACE INTO raw_signals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(signal.id),
                        str(signal.source_id) if signal.source_id else None,
                        signal.source_name,
                        signal.feed_url,
                        signal.feed_title,
                        signal.original_url,
                        signal.original_title,
                        signal.original_summary,
                        signal.original_content,
                        signal.original_html,
                        signal.original_image_url,
                        signal.original_author,
                        signal.original_language,
                        tags_json,
                        signal.published_at.isoformat() if signal.published_at else None,
                        signal.url_hash,
                        signal.title_hash,
                        signal.content_hash,
                        signal.word_count,
                        1 if signal.has_image else 0,
                        1 if signal.was_processed else 0,
                        str(signal.article_id) if signal.article_id else None,
                        signal.processing_result,
                        signal.processing_note,
                        signal.processed_at.isoformat() if signal.processed_at else None,
                        1 if signal.is_archived else 0,
                        signal.archived_at.isoformat() if signal.archived_at else None,
                        signal.created_at.isoformat() if signal.created_at else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to archive signal {signal.id}: {e}")

            conn.commit()
            conn.close()

        logger.info(f"Archived {len(signals)} signals to {db_path}")
        return len(signals)

    def write_articles(self, year: int, month: int, articles: list) -> int:
        """Archive articles for the specified month - includes ALL states."""
        if not articles:
            return 0

        db_path = self.get_db_path("articles", year, month)
        file_lock = self._get_file_lock(db_path)

        with file_lock:
            conn = self._get_connection(db_path)
            self._ensure_table_exists(conn, "articles")

            for article in articles:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(article.id),
                        str(article.source_id) if article.source_id else None,
                        article.original_url,
                        article.original_title,
                        article.title_hash,
                        article.original_summary,
                        article.original_image_url,
                        article.signal_published_at.isoformat() if article.signal_published_at else None,
                        article.category,
                        article.category_confidence,
                        article.trend_score,
                        article.article_type,
                        article.crawled_content,
                        json.dumps(article.crawled_images) if article.crawled_images else "[]",
                        article.body_html,
                        article.meta_title,
                        article.meta_description,
                        article.slug,
                        json.dumps(article.tags) if article.tags else "[]",
                        json.dumps(article.image_keywords) if article.image_keywords else "[]",
                        article.word_count,
                        article.governance_result,
                        article.governance_reason,
                        article.copyright_score,
                        article.wp_post_id,
                        article.wp_url,
                        article.featured_image_wp_id,
                        article.image_source_credit,
                        article.published_at.isoformat() if article.published_at else None,
                        article.state,
                        article.mode,
                        article.priority,
                        article.queued_at.isoformat() if article.queued_at else None,
                        article.fail_reason,
                        article.retry_count,
                        article.last_step_at.isoformat() if article.last_step_at else None,
                        article.created_at.isoformat() if article.created_at else None,
                        article.updated_at.isoformat() if article.updated_at else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to archive article {article.id}: {e}")

            conn.commit()
            conn.close()

        logger.info(f"Archived {len(articles)} articles to {db_path}")
        return len(articles)

    def write_predictions(self, year: int, month: int, predictions: list) -> int:
        """Archive predictions for the specified month."""
        if not predictions:
            return 0

        db_path = self.get_db_path("predictions", year, month)
        file_lock = self._get_file_lock(db_path)

        with file_lock:
            conn = self._get_connection(db_path)
            self._ensure_table_exists(conn, "predictions")

            for pred in predictions:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO prediction_final VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(pred.id),
                        pred.symbol,
                        pred.prediction_date.isoformat() if hasattr(pred.prediction_date, 'isoformat') else str(pred.prediction_date),
                        pred.horizon_days,
                        float(pred.current_price) if pred.current_price else None,
                        float(pred.predicted_price),
                        float(pred.predicted_low) if pred.predicted_low else None,
                        float(pred.predicted_high) if pred.predicted_high else None,
                        float(pred.change_pct) if pred.change_pct else None,
                        float(pred.confidence_score) if pred.confidence_score else None,
                        float(pred.timesfm_prediction) if pred.timesfm_prediction else None,
                        float(pred.chronos_prediction) if pred.chronos_prediction else None,
                        float(pred.ensemble_weight_timesfm) if pred.ensemble_weight_timesfm else None,
                        float(pred.ensemble_weight_chronos) if pred.ensemble_weight_chronos else None,
                        pred.ai_sentiment,
                        float(pred.ai_sentiment_score) if pred.ai_sentiment_score else None,
                        float(pred.ai_adjustment_pct) if pred.ai_adjustment_pct else None,
                        json.dumps(pred.technical_signals) if pred.technical_signals else "{}",
                        pred.model_used,
                        float(pred.actual_price) if pred.actual_price else None,
                        float(pred.accuracy_error_pct) if pred.accuracy_error_pct else None,
                        pred.generated_at.isoformat() if pred.generated_at else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to archive prediction {pred.id}: {e}")

            conn.commit()
            conn.close()

        logger.info(f"Archived {len(predictions)} predictions to {db_path}")
        return len(predictions)

    def write_market_research(self, year: int, month: int, research: list) -> int:
        """Archive market research for the specified month."""
        if not research:
            return 0

        db_path = self.get_db_path("market_research", year, month)
        file_lock = self._get_file_lock(db_path)

        with file_lock:
            conn = self._get_connection(db_path)
            self._ensure_table_exists(conn, "market_research")

            for item in research:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO market_research VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(item.id),
                        item.symbol,
                        item.analysis_date.isoformat() if hasattr(item.analysis_date, 'isoformat') else str(item.analysis_date),
                        item.sentiment,
                        float(item.sentiment_score) if item.sentiment_score else None,
                        item.analysis_text,
                        item.analysis_vi,
                        json.dumps(item.key_factors) if item.key_factors else "[]",
                        json.dumps(item.risk_factors) if item.risk_factors else "[]",
                        json.dumps(item.support_levels) if item.support_levels else "[]",
                        json.dumps(item.resistance_levels) if item.resistance_levels else "[]",
                        item.fear_greed_index,
                        item.fear_greed_value,
                        item.model_used,
                        float(item.confidence_score) if item.confidence_score else None,
                        item.generated_at.isoformat() if item.generated_at else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to archive market research {item.id}: {e}")

            conn.commit()
            conn.close()

        logger.info(f"Archived {len(research)} market research to {db_path}")
        return len(research)

    def get_archive_stats(self) -> dict:
        """Return stats for all archive files."""
        stats = {}
        for data_type in ["signals", "articles", "predictions", "market_research"]:
            dir_path = os.path.join(self.base_dir, data_type)
            if os.path.exists(dir_path):
                files = glob.glob(os.path.join(dir_path, "*.db"))
                total_size = sum(os.path.getsize(f) for f in files)
                file_dates = []
                for f in files:
                    try:
                        basename = os.path.basename(f)
                        parts = basename.replace(".db", "").split("-")
                        file_dates.append(f"{parts[0]}-{parts[1]}")
                    except Exception:
                        pass

                stats[data_type] = {
                    "files": len(files),
                    "total_size_mb": round(total_size / 1024 / 1024, 1),
                    "oldest": min(file_dates) if file_dates else None,
                    "newest": max(file_dates) if file_dates else None,
                }
            else:
                stats[data_type] = {
                    "files": 0,
                    "total_size_mb": 0,
                    "oldest": None,
                    "newest": None,
                }
        return stats
