"""
Tests for core pipeline functionality.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


class TestArticleStateMachine:
    """Test cases for Article state machine."""

    def test_article_states_defined(self):
        """Test that all article states are properly defined."""
        from app.models.article import ArticleState
        
        expected_states = [
            "SIGNAL_COLLECTED",
            "CATEGORIZED",
            "TRENDING",
            "SKIPPED",
            "EXPIRED",
            "RESEARCHED",
            "WRITTEN",
            "GOVERNED",
            "APPROVED",
            "REJECTED",
            "PUBLISHED",
            "FAILED",
        ]
        
        for state in expected_states:
            assert hasattr(ArticleState, state), f"Missing state: {state}"

    def test_article_mode_defined(self):
        """Test that article modes are properly defined."""
        from app.models.article import ArticleMode
        
        assert hasattr(ArticleMode, "NORMAL")
        assert hasattr(ArticleMode, "ALLIN")
        assert ArticleMode.NORMAL.value == "normal"
        assert ArticleMode.ALLIN.value == "allin"


class TestPipelineControl:
    """Test cases for pipeline control module."""

    @pytest.mark.asyncio
    async def test_pipeline_state_enum(self):
        """Test pipeline state enum values."""
        from app.pipeline.control import PipelineState
        
        assert PipelineState.STOPPED.value == "stopped"
        assert PipelineState.RUNNING.value == "running"
        assert PipelineState.PAUSED.value == "paused"
        assert PipelineState.STOPPING.value == "stopping"

    @pytest.mark.asyncio
    async def test_pipeline_mode_enum(self):
        """Test pipeline mode enum values."""
        from app.pipeline.control import PipelineMode
        
        assert PipelineMode.NORMAL.value == "normal"
        assert PipelineMode.ALLIN.value == "allin"
        assert PipelineMode.CONTINUOUS.value == "continuous"


class TestHardStop:
    """Test cases for hard stop mechanism."""

    def test_hard_stop_functions_exist(self):
        """Test that hard stop functions are properly defined."""
        from app.pipeline.hard_stop import (
            trigger_user_stop,
            clear_user_stop,
            should_stop_pipeline,
            get_stop_status,
        )
        from app.pipeline.control import is_pipeline_stopped

        assert callable(trigger_user_stop)
        assert callable(clear_user_stop)
        assert callable(should_stop_pipeline)
        assert callable(get_stop_status)
        assert callable(is_pipeline_stopped)


class TestQueueManager:
    """Test cases for queue manager."""

    def test_queue_manager_functions_exist(self):
        """Test that queue manager functions are properly defined."""
        from app.pipeline.queue_manager import (
            get_next_articles,
            queue_articles,
            get_queue_stats,
            expire_old_signals,
        )
        
        assert callable(get_next_articles)
        assert callable(queue_articles)
        assert callable(get_queue_stats)
        assert callable(expire_old_signals)


class TestPipelineTasks:
    """Test cases for pipeline tasks."""

    def test_pipeline_task_functions_exist(self):
        """Test that pipeline task functions are properly defined."""
        from app.pipeline.tasks import (
            task_categorize,
            task_score_trend,
            task_research,
            task_write,
            task_govern,
            task_publish,
            run_normal_pipeline,
            run_allin_pipeline,
        )
        
        assert callable(task_categorize)
        assert callable(task_score_trend)
        assert callable(task_research)
        assert callable(task_write)
        assert callable(task_govern)
        assert callable(task_publish)
        assert callable(run_normal_pipeline)
        assert callable(run_allin_pipeline)


class TestLocks:
    """Test cases for distributed locks."""

    def test_lock_classes_exist(self):
        """Test that lock classes are properly defined."""
        from app.core.locks import (
            article_lock,
            title_lock,
            DistributionLock,
            is_article_locked,
            is_title_locked,
        )
        
        assert callable(article_lock)
        assert callable(title_lock)
        assert callable(DistributionLock)
        assert callable(is_article_locked)
        assert callable(is_title_locked)


class TestDedup:
    """Test cases for deduplication."""

    def test_semantic_dedup_threshold(self):
        """Test semantic dedup threshold is reasonable."""
        from app.signals.service import SEMANTIC_THRESHOLD
        
        # Threshold should be between 0 and 1
        assert 0 < SEMANTIC_THRESHOLD < 1
        # Current threshold is 0.35
        assert SEMANTIC_THRESHOLD == 0.35

    def test_keyword_extraction(self):
        """Test keyword extraction from title."""
        from app.signals.service import extract_keywords
        
        keywords = extract_keywords("OpenAI launches GPT-5 with advanced capabilities")
        
        # Should remove common stopwords
        assert "the" not in keywords
        assert "with" not in keywords
        assert "a" not in keywords
        
        # Should keep meaningful words
        assert len(keywords) > 0

    def test_keyword_similarity(self):
        """Test keyword similarity calculation."""
        from app.signals.service import keyword_similarity
        
        # Same title should have similarity 1.0
        sim = keyword_similarity("AI GPT-5 launches", "AI GPT-5 launches")
        assert sim == 1.0
        
        # Completely different titles should have similarity 0
        sim = keyword_similarity("Apple releases iPhone", "Microsoft Windows update")
        # These share no keywords after stopword removal, so should be 0
        # "Apple", "releases", "iPhone" vs "Microsoft", "Windows", "update"
        # No common words after stopword removal
        assert sim == 0


class TestGovernance:
    """Test cases for governance module."""

    def test_governor_functions_exist(self):
        """Test that governor functions are properly defined."""
        from app.pipeline.governor import govern_article
        
        assert callable(govern_article)


class TestAnalyzer:
    """Test cases for analyzer module."""

    def test_analyzer_functions_exist(self):
        """Test that analyzer functions are properly defined."""
        from app.pipeline.analyzer import (
            categorize_article,
            score_article_trend,
        )
        
        assert callable(categorize_article)
        assert callable(score_article_trend)


class TestWriter:
    """Test cases for writer module."""

    def test_writer_functions_exist(self):
        """Test that writer functions are properly defined."""
        from app.pipeline.writer import write_article
        
        assert callable(write_article)
