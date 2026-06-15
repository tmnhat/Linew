"""Tests for governance module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCheckCopyright:
    def test_copyright_similarity_same_text(self):
        from app.pipeline.governor import check_copyright
        ratio = check_copyright("Hello world this is a test", "Hello world this is a test")
        assert ratio > 0.9

    def test_copyright_similarity_different_text(self):
        from app.pipeline.governor import check_copyright
        ratio = check_copyright("Apple announces new iPhone model", "Bitcoin surges past 100k")
        assert ratio < 0.3

    def test_copyright_empty_content(self):
        from app.pipeline.governor import check_copyright
        ratio = check_copyright("", "Some content")
        assert ratio == 0.0


class TestSignalDedup:
    def test_keyword_similarity_identical(self):
        from app.signals.service import keyword_similarity
        sim = keyword_similarity("FPT tăng trưởng mạnh quý 1", "FPT tăng trưởng mạnh quý 1")
        assert sim == 1.0

    def test_keyword_similarity_unrelated(self):
        from app.signals.service import keyword_similarity
        sim = keyword_similarity("Bitcoin giảm mạnh", "FPT ra mắt sản phẩm mới")
        assert sim < 0.2
